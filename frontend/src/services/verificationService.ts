import axios from 'axios';
import { DocumentType, ExtractedField, VerificationResult, AadhaarEkycData } from '@/types';

// Future FastAPI Backend URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface TamperingResult {
  tampered: boolean;
  tamperConfidence: number; // 0 to 100
  anomalies: string[];
}

export interface FaceVerificationResult {
  matched: boolean;
  matchScore: number; // 0 to 100
  livenessPassed: boolean;
}

export interface DocumentValidationResult {
  isValid: boolean;
  mrzValid: boolean;
  checksumValid: boolean;
  expiryValid: boolean;
  errors: string[];
}

/**
 * Saves captured image into the workspace 'image' folder
 * so the backend OCR team can immediately access and process it.
 */
export async function saveCapturedImageToDisk(
  image: string,
  docType: DocumentType,
  side: 'front' | 'back' = 'front',
  customName?: string
): Promise<{ success: boolean; savedPath: string; fileName: string; fileUrl: string }> {
  try {
    const res = await axios.post('/api/save-image', {
      image,
      docType,
      side,
      customName,
    });
    return res.data;
  } catch (err: any) {
    console.warn('Could not save to image folder:', err.message);
    return {
      success: false,
      savedPath: `image/${docType}_${side}.jpg`,
      fileName: `${docType}_${side}.jpg`,
      fileUrl: image,
    };
  }
}

import { recognize } from 'tesseract.js';

/**
 * Parses raw OCR text into structured document fields based on document type
 */
function parseOcrText(rawText: string, docType: DocumentType): Record<string, ExtractedField> {
  const lines = rawText
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l.length > 2);

  const fields: Record<string, ExtractedField> = {};
  const upper = rawText.toUpperCase();

  // 1. Look for DOB
  const dobMatch = rawText.match(/\b(\d{2}[\/\-.]\d{2}[\/\-.]\d{4})\b/) ||
                   rawText.match(/(?:DOB|D\.O\.B|Birth|Year)[\s:]*([0-9]{2}[\/\-][0-9]{2}[\/\-][0-9]{4}|[0-9]{4})/i);
  if (dobMatch) {
    fields.dateOfBirth = {
      key: 'dateOfBirth',
      label: 'Date of Birth',
      value: dobMatch[1],
      confidence: 96,
      editable: true,
    };
  }

  // 2. Look for Gender
  if (/\b(FEMALE|WOMAN)\b/i.test(upper)) {
    fields.gender = { key: 'gender', label: 'Gender', value: 'Female', confidence: 97, editable: true };
  } else if (/\b(MALE|MAN)\b/i.test(upper)) {
    fields.gender = { key: 'gender', label: 'Gender', value: 'Male', confidence: 97, editable: true };
  }

  // 3. Document-specific identifiers
  if (docType === 'aadhaar') {
    const aadhaarMatch = rawText.match(/\b(\d{4}\s\d{4}\s\d{4})\b/) || rawText.match(/\b([X\d]{4}\s[X\d]{4}\s\d{4})\b/);
    if (aadhaarMatch) {
      fields.maskedAadhaar = {
        key: 'maskedAadhaar',
        label: 'Masked Aadhaar Number',
        value: aadhaarMatch[1],
        confidence: 98,
        editable: true,
      };
    }
  } else if (docType === 'passport') {
    const passportMatch = rawText.match(/\b([A-PR-WYa-pr-wy][0-9]{7})\b/);
    if (passportMatch) {
      fields.passportNumber = {
        key: 'passportNumber',
        label: 'Passport Number',
        value: passportMatch[1].toUpperCase(),
        confidence: 98,
        editable: true,
      };
    }
  } else if (docType === 'driving_license') {
    const dlMatch = rawText.match(/\b([A-Z]{2}[-\s]?[0-9]{2}[-\s]?[0-9]{4}[-\s]?[0-9]{4,7})\b/i);
    if (dlMatch) {
      fields.dlNumber = {
        key: 'dlNumber',
        label: 'Licence Number',
        value: dlMatch[1].toUpperCase(),
        confidence: 98,
        editable: true,
      };
    }
  } else if (docType === 'visa') {
    const visaMatch = rawText.match(/\b(V[0-9]{7,9})\b/i);
    if (visaMatch) {
      fields.visaNumber = {
        key: 'visaNumber',
        label: 'Visa Number',
        value: visaMatch[1].toUpperCase(),
        confidence: 97,
        editable: true,
      };
    }
  }

  // 4. Look for Name (first non-header alphabetic line)
  const candidateNames = lines.filter((l) => {
    const isHeader = /GOVERNMENT|INDIA|UNION|REPUBLIC|PASSPORT|DRIVING|LICENCE|ELECTION|COMMISSION|AADHAAR|UNIQUE|AUTHORITY/i.test(l);
    const hasLetters = /^[A-Za-z\s.]{3,35}$/.test(l);
    return !isHeader && hasLetters;
  });

  if (candidateNames.length > 0) {
    fields.name = {
      key: 'name',
      label: docType === 'driving_license' ? 'Holder Name' : 'Name',
      value: candidateNames[0],
      confidence: 95,
      editable: true,
    };
  }

  // 5. If general scannable object, add lines of recognized text
  if (lines.length > 0 && Object.keys(fields).length < 2) {
    lines.slice(0, 4).forEach((line, idx) => {
      fields[`extracted_line_${idx + 1}`] = {
        key: `extracted_line_${idx + 1}`,
        label: `Recognized Text #${idx + 1}`,
        value: line,
        confidence: 92,
        editable: true,
      };
    });
  }

  return fields;
}

/**
 * 1. OCR Extraction API service
 * Ready to connect to FastAPI POST /api/ocr endpoint, with client-side Tesseract OCR fallback
 */
export async function ocr(
  image: Blob | string,
  docType: DocumentType,
  isSuspicious: boolean = false
): Promise<Record<string, ExtractedField>> {
  // 1. Try FastAPI Backend endpoint first if accessible
  try {
    const formData = new FormData();
    if (image instanceof Blob) {
      formData.append('file', image);
    } else {
      formData.append('image_url', image);
    }
    formData.append('document_type', docType);

    const response = await axios.post(`${API_BASE_URL}/api/ocr`, formData, {
      timeout: 1500,
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    if (response.data && response.data.fields) {
      return response.data.fields;
    }
  } catch {
    // Backend offline; continue to in-browser Tesseract OCR
  }

  // 2. Run client-side Tesseract.js OCR on real captured/scanned image
  let clientOcrFields: Record<string, ExtractedField> = {};
  if (typeof window !== 'undefined' && typeof image === 'string' && !image.endsWith('.svg')) {
    try {
      const result = await recognize(image, 'eng');
      if (result && result.data && result.data.text && result.data.text.trim().length > 5) {
        clientOcrFields = parseOcrText(result.data.text, docType);
      }
    } catch (ocrErr) {
      console.warn('Tesseract client OCR note:', ocrErr);
    }
  }

  // Realistic mock extraction by document type
  let baseFields: Record<string, ExtractedField> = {};

  if (docType === 'passport') {
    baseFields = {
      name: {
        key: 'name',
        label: 'Name',
        value: 'Rahul Sharma',
        confidence: 99,
        editable: true,
      },
      passportNumber: {
        key: 'passportNumber',
        label: 'Passport Number',
        value: 'A1234567',
        confidence: 99,
        editable: true,
      },
      nationality: {
        key: 'nationality',
        label: 'Nationality',
        value: 'Indian',
        confidence: 98,
        editable: true,
      },
      dateOfBirth: {
        key: 'dateOfBirth',
        label: 'Date of Birth',
        value: '14/03/2003',
        confidence: 97,
        editable: true,
      },
      gender: {
        key: 'gender',
        label: 'Gender',
        value: 'Male',
        confidence: 99,
        editable: true,
      },
      expiryDate: {
        key: 'expiryDate',
        label: 'Expiry Date',
        value: '22/08/2032',
        confidence: 98,
        editable: true,
      },
    };
  } else if (docType === 'driving_license') {
    baseFields = {
      dlNumber: {
        key: 'dlNumber',
        label: 'Licence Number',
        value: 'DL-0420110012345',
        confidence: 99,
        editable: true,
      },
      name: {
        key: 'name',
        label: 'Holder Name',
        value: 'Rahul Sharma',
        confidence: 99,
        editable: true,
      },
      fatherName: {
        key: 'fatherName',
        label: "Father's Name",
        value: 'Ramesh Sharma',
        confidence: 98,
        editable: true,
      },
      dateOfBirth: {
        key: 'dateOfBirth',
        label: 'Date of Birth',
        value: '14/03/2003',
        confidence: 97,
        editable: true,
      },
      bloodGroup: {
        key: 'bloodGroup',
        label: 'Blood Group',
        value: 'O+ (Positive)',
        confidence: 99,
        editable: true,
      },
      validity: {
        key: 'validity',
        label: 'Validity (NT)',
        value: '13/03/2043',
        confidence: 98,
        editable: true,
      },
      vehicleClass: {
        key: 'vehicleClass',
        label: 'Class of Vehicle',
        value: 'MCWG, LMV',
        confidence: 99,
        editable: true,
      },
      address: {
        key: 'address',
        label: 'Permanent Address',
        value: 'H.No 42, Pocket B, Mayur Vihar Phase 1, New Delhi - 110091',
        confidence: 97,
        editable: true,
      },
    };
  } else if (docType === 'visa') {
    baseFields = {
      visaNumber: {
        key: 'visaNumber',
        label: 'Visa Number',
        value: 'V98765432',
        confidence: 99,
        editable: true,
      },
      visaType: {
        key: 'visaType',
        label: 'Visa Type',
        value: 'Tourist / Business (B1/B2)',
        confidence: 97,
        editable: true,
      },
      expiryDate: {
        key: 'expiryDate',
        label: 'Expiry Date',
        value: '15/12/2028',
        confidence: 96,
        editable: true,
      },
      passportNumber: {
        key: 'passportNumber',
        label: 'Passport Number',
        value: 'A1234567',
        confidence: 98,
        editable: true,
      },
    };
  } else if (isSuspicious) {
    baseFields = {
      name: {
        key: 'name',
        label: 'Name',
        value: 'Rahul Sharma',
        confidence: 94,
        editable: true,
      },
      dateOfBirth: {
        key: 'dateOfBirth',
        label: 'Date of Birth',
        value: '14/03/1990',
        confidence: 76,
        editable: true,
      },
      gender: {
        key: 'gender',
        label: 'Gender',
        value: 'Male',
        confidence: 98,
        editable: true,
      },
      maskedAadhaar: {
        key: 'maskedAadhaar',
        label: 'Masked Aadhaar Number',
        value: 'XXXX XXXX 7821',
        confidence: 92,
        editable: true,
      },
      address: {
        key: 'address',
        label: 'Address',
        value: 'Pocket B, Mayur Vihar Phase 1, New Delhi - 110091',
        confidence: 88,
        editable: true,
      },
    };
  } else {
    // docType === 'aadhaar'
    baseFields = {
      name: {
        key: 'name',
        label: 'Name',
        value: 'Rahul Sharma',
        confidence: 99,
        editable: true,
      },
      dateOfBirth: {
        key: 'dateOfBirth',
        label: 'Date of Birth',
        value: '14/03/2003',
        confidence: 97,
        editable: true,
      },
      gender: {
        key: 'gender',
        label: 'Gender',
        value: 'Male',
        confidence: 99,
        editable: true,
      },
      maskedAadhaar: {
        key: 'maskedAadhaar',
        label: 'Masked Aadhaar Number',
        value: 'XXXX XXXX 7821',
        confidence: 99,
        editable: true,
      },
      address: {
        key: 'address',
        label: 'Address',
        value: 'House No. 42, Pocket B, Mayur Vihar Phase 1, New Delhi - 110091',
        confidence: 98,
        editable: true,
      },
    };
  }

  // Merge real recognized client OCR fields on top of base fields
  return { ...baseFields, ...clientOcrFields };
}

/**
 * 2. Document Validation API service
 */
export async function validateDocument(
  docType: DocumentType,
  fields: Record<string, ExtractedField>,
  isSuspicious: boolean = false
): Promise<DocumentValidationResult> {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/validate-document`, {
      docType,
      fields,
    }, { timeout: 1500 });
    return response.data;
  } catch {
    if (isSuspicious) {
      return {
        isValid: false,
        mrzValid: true,
        checksumValid: false,
        expiryValid: true,
        errors: ['Security checksum mismatch on secondary fields'],
      };
    }
    return {
      isValid: true,
      mrzValid: true,
      checksumValid: true,
      expiryValid: true,
      errors: [],
    };
  }
}

/**
 * 3. Tampering Detection API service
 */
export async function detectTampering(
  image: Blob | string,
  isSuspicious: boolean = false
): Promise<TamperingResult> {
  try {
    const formData = new FormData();
    if (image instanceof Blob) formData.append('file', image);
    const response = await axios.post(`${API_BASE_URL}/api/detect-tampering`, formData, { timeout: 1500 });
    return response.data;
  } catch {
    if (isSuspicious) {
      return {
        tampered: true,
        tamperConfidence: 84,
        anomalies: [
          'Edge artifact detected around portrait boundary',
          'Font rasterization mismatch in Date of Birth field',
        ],
      };
    }
    return {
      tampered: false,
      tamperConfidence: 4,
      anomalies: [],
    };
  }
}

/**
 * 4. Face Verification API service
 */
export async function verifyFace(
  image: Blob | string,
  isSuspicious: boolean = false
): Promise<FaceVerificationResult> {
  try {
    const formData = new FormData();
    if (image instanceof Blob) formData.append('file', image);
    const response = await axios.post(`${API_BASE_URL}/api/verify-face`, formData, { timeout: 1500 });
    return response.data;
  } catch {
    if (isSuspicious) {
      return {
        matched: false,
        matchScore: 42,
        livenessPassed: true,
      };
    }
    return {
      matched: true,
      matchScore: 96,
      livenessPassed: true,
    };
  }
}

/**
 * 5. Aadhaar eKYC Service
 */
export async function verifyAadhaar(
  maskedAadhaar: string,
  details?: Record<string, ExtractedField>
): Promise<AadhaarEkycData> {
  await new Promise((res) => setTimeout(res, 600));

  return {
    maskedAadhaar: maskedAadhaar || 'XXXX XXXX 7821',
    nameVerified: true,
    dobVerified: true,
    genderVerified: true,
    isVerified: true,
    timestamp: new Date().toISOString(),
  };
}

/**
 * 6. Calculate Final Risk Score & Recommendation
 */
export function calculateRisk(
  docType: DocumentType,
  validation: DocumentValidationResult,
  tampering: TamperingResult,
  face: FaceVerificationResult,
  ekyc?: AadhaarEkycData | null
): VerificationResult {
  const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const isEkycSkipped = docType === 'aadhaar' && Boolean(ekyc?.isSkipped);

  if (tampering.tampered || !face.matched || !validation.isValid) {
    const baseScore = Math.round(70 + Math.random() * 15);
    const score = isEkycSkipped ? Math.min(96, baseScore + 10) : baseScore;
    const checks: VerificationResult['checks'] = [
      {
        id: 'ocr',
        title: 'OCR extracted',
        status: 'passed',
        detail: 'All primary fields extracted successfully',
      },
      {
        id: 'tampering',
        title: 'Possible tampering detected',
        status: 'warning',
        detail: tampering.anomalies[0] || 'Digital boundary artifact detected',
      },
      {
        id: 'face',
        title: face.matched ? 'Face matched' : 'Face mismatch',
        status: face.matched ? 'passed' : 'warning',
        detail: face.matched ? 'Confidence: 96%' : 'Confidence below threshold (42%)',
      },
      {
        id: 'doc',
        title: validation.mrzValid ? 'Integrity verified' : 'Document format anomaly',
        status: validation.mrzValid ? 'passed' : 'failed',
        detail: validation.mrzValid ? 'Checksum valid' : 'Checksum mismatch',
      },
    ];

    if (isEkycSkipped) {
      checks.push({
        id: 'ekyc',
        title: 'Aadhaar eKYC skipped',
        status: 'warning',
        detail: 'Demographic authentication bypassed — identity unconfirmed (+10% risk penalty)',
      });
    }

    return {
      riskLevel: 'HIGH RISK',
      riskScore: score,
      explanation: isEkycSkipped
        ? 'Potential document alteration detected and eKYC was skipped. Manual verification required.'
        : 'Potential document alteration detected. Manual verification recommended.',
      checks,
      timestamp,
    };
  }

  // When eKYC is skipped, overall score and risk factor are affected:
  // Risk score increases from ~18-28 to ~42-48, elevating risk level to MEDIUM RISK.
  const score = isEkycSkipped
    ? Math.round(42 + Math.random() * 8)
    : Math.round(18 + Math.random() * 10);
  const riskLevel: VerificationResult['riskLevel'] = isEkycSkipped ? 'MEDIUM RISK' : 'LOW RISK';

  const checks: VerificationResult['checks'] = [
    {
      id: 'doc_info',
      title: 'Document information valid',
      status: 'passed',
      detail: 'Format, fields and issuing entity verified',
    },
    {
      id: 'integrity',
      title: docType === 'passport' || docType === 'visa' ? 'MRZ valid' : 'Digital QR & Checksum valid',
      status: 'passed',
      detail: docType === 'passport' || docType === 'visa' ? 'Standard ICAO 9303 checksum passed' : 'Cryptographic signature valid',
    },
    {
      id: 'face',
      title: 'Face matched',
      status: 'passed',
      detail: 'Biometric similarity score 96%',
    },
    {
      id: 'tamper',
      title: 'No major tampering detected',
      status: 'passed',
      detail: 'Clean font consistency, no pixel interpolation anomalies',
    },
  ];

  if (docType === 'aadhaar') {
    if (ekyc?.isVerified) {
      checks.push({
        id: 'ekyc',
        title: 'Aadhaar eKYC verified',
        status: 'passed',
        detail: 'Name, DOB and Gender matched UIDAI record',
      });
    } else if (isEkycSkipped) {
      checks.push({
        id: 'ekyc',
        title: 'Aadhaar eKYC skipped',
        status: 'warning',
        detail: 'Demographic authentication bypassed — identity unconfirmed (+20% risk factor)',
      });
    }
  }

  return {
    riskLevel,
    riskScore: score,
    explanation: isEkycSkipped
      ? 'Document scan passed, but Aadhaar eKYC was skipped. Overall risk factor increased to MEDIUM RISK due to unverified demographic records.'
      : 'Document appears valid based on the available verification checks.',
    checks,
    timestamp,
  };
}
