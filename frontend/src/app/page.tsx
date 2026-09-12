"use client";
import React, { useState } from 'react';
import WebCamScanner, { ScanSessionPayload } from '@/components/scanner/WebCamScanner';
import ManualCropWrapper from '@/components/scanner/ManualCropWrapper';
import ScanReviewScreen from '@/components/workflow/ScanReviewScreen';
import DocumentTypeScreen, { UnavailableDocFlags, DocChecklistEntry } from '@/components/workflow/DocumentTypeScreen';
import ExtractionScreen from '@/components/workflow/ExtractionScreen';
import VerificationScreen from '@/components/workflow/VerificationScreen';
import AadhaarEkycScreen from '@/components/workflow/AadhaarEkycScreen';
import FinalResultScreen from '@/components/workflow/FinalResultScreen';
import HistoryView from '@/components/history/HistoryView';
import SettingsView from '@/components/settings/SettingsView';

import {
  ocr,
  validateDocument,
  detectTampering,
  verifyFace,
  calculateRisk,
} from '@/services/verificationService';
import {
  DocumentType,
  ExtractedField,
  VerificationResult,
  HistoryItem,
  AadhaarEkycData,
} from '@/types';
import { Point, processScanWithFallback } from '@/utils/scannerUtils';
import { CapturedDoc } from '@/components/scanner/WebCamScanner';
import { Camera, History, Settings } from 'lucide-react';

type WorkflowStep =
  | 'scanner'
  | 'crop'
  | 'review'
  | 'doc-type'
  | 'extract'
  | 'verify'
  | 'ekyc'
  | 'result';

export default function SecureScanApp() {
  const [activeTab, setActiveTab] = useState<'scan' | 'history' | 'settings'>('scan');
  const [step, setStep] = useState<WorkflowStep>('scanner');

  // Active Session State
  const [rawImage, setRawImage] = useState<string>('');
  const [processedImage, setProcessedImage] = useState<string>('');
  const [backRawImage, setBackRawImage] = useState<string | undefined>();
  const [backProcessedImage, setBackProcessedImage] = useState<string | undefined>();
  const [savedFilePaths, setSavedFilePaths] = useState<{ front?: string; back?: string }>({});

  const [corners, setCorners] = useState<Point[]>([]);
  const [detectedType, setDetectedType] = useState<DocumentType>('aadhaar');
  const [confidence, setConfidence] = useState<number>(98);
  const [fileName, setFileName] = useState<string>('aadhaar_001');
  const [isSuspicious, setIsSuspicious] = useState<boolean>(false);
  const [extractedFields, setExtractedFields] = useState<Record<string, ExtractedField>>({});
  const [ekycData, setEkycData] = useState<AadhaarEkycData | null>(null);
  const [finalResult, setFinalResult] = useState<VerificationResult | null>(null);
  const [unavailableDocs, setUnavailableDocs] = useState<UnavailableDocFlags>({
    aadhaar: false,
    driving_license: false,
    passport: false,
    visa: false,
  });

  // All docs captured in the current session (for gallery review)
  const [sessionDocs, setSessionDocs] = useState<CapturedDoc[]>([]);

  // Checklist from DocumentTypeScreen (all docs with status)
  const [sessionChecklist, setSessionChecklist] = useState<DocChecklistEntry[]>([]);

  // OCR fields keyed by docType — holds results for ALL scanned docs
  const [allDocFields, setAllDocFields] = useState<Record<string, Record<string, ExtractedField>>>({}); 

  // Pre-populated History items with all requested document presets
  const [history, setHistory] = useState<HistoryItem[]>([
    {
      id: 'scan-001',
      documentType: 'passport',
      fileName: 'passport_001',
      holderName: 'Rahul Sharma',
      identifier: 'A1234567',
      riskLevel: 'LOW',
      riskScore: 24,
      timeAgo: '2 minutes ago',
      timestamp: Date.now() - 120000,
      imageThumbnail: '/samples/passport_front.svg',
      ekycVerified: false,
      result: {
        riskLevel: 'LOW RISK',
        riskScore: 24,
        explanation: 'Document appears valid based on the available verification checks.',
        checks: [
          { id: 'doc_info', title: 'Document information valid', status: 'passed', detail: 'Format & fields verified' },
          { id: 'mrz', title: 'MRZ valid', status: 'passed', detail: 'ICAO 9303 checksum passed' },
          { id: 'face', title: 'Face matched', status: 'passed', detail: 'Biometric similarity score 96%' },
          { id: 'tamper', title: 'No major tampering detected', status: 'passed', detail: 'No manipulation detected' },
        ],
        timestamp: '10:42 PM',
      },
      extractedFields: {
        name: { key: 'name', label: 'Name', value: 'Rahul Sharma', confidence: 99 },
        passportNumber: { key: 'passportNumber', label: 'Passport Number', value: 'A1234567', confidence: 99 },
        nationality: { key: 'nationality', label: 'Nationality', value: 'Indian', confidence: 98 },
        dateOfBirth: { key: 'dateOfBirth', label: 'Date of Birth', value: '14/03/2003', confidence: 97 },
      },
      savedPaths: { front: 'image/passport_front.svg' },
    },
    {
      id: 'scan-002',
      documentType: 'driving_license',
      fileName: 'driving_license_001',
      holderName: 'Rahul Sharma',
      identifier: 'DL-0420110012345',
      riskLevel: 'LOW',
      riskScore: 19,
      timeAgo: '15 minutes ago',
      timestamp: Date.now() - 900000,
      imageThumbnail: '/samples/driving_license_front.svg',
      backThumbnail: '/samples/driving_license_back.svg',
      ekycVerified: false,
      result: {
        riskLevel: 'LOW RISK',
        riskScore: 19,
        explanation: 'Driving Licence verified against Parivahan Sarathi registry format.',
        checks: [
          { id: 'doc_info', title: 'DL number format valid', status: 'passed', detail: 'DL-0420110012345 format matched' },
          { id: 'cov', title: 'COV classes valid', status: 'passed', detail: 'MCWG & LMV authorized' },
          { id: 'face', title: 'Face matched', status: 'passed', detail: 'Biometric similarity score 95%' },
          { id: 'tamper', title: 'Smart chip integrity valid', status: 'passed', detail: 'No digital forgery detected' },
        ],
        timestamp: '10:29 PM',
      },
      extractedFields: {
        dlNumber: { key: 'dlNumber', label: 'Licence Number', value: 'DL-0420110012345', confidence: 99 },
        name: { key: 'name', label: 'Holder Name', value: 'Rahul Sharma', confidence: 99 },
        validity: { key: 'validity', label: 'Validity (NT)', value: '13/03/2043', confidence: 98 },
      },
      savedPaths: {
        front: 'image/driving_license_front.svg',
        back: 'image/driving_license_back.svg',
      },
    },
    {
      id: 'scan-003',
      documentType: 'visa',
      fileName: 'visa_001',
      holderName: 'Rahul Sharma',
      identifier: 'V98765432',
      riskLevel: 'MEDIUM',
      riskScore: 48,
      timeAgo: 'Yesterday',
      timestamp: Date.now() - 86400000,
      imageThumbnail: '/samples/visa_front.svg',
      ekycVerified: false,
      result: {
        riskLevel: 'MEDIUM RISK',
        riskScore: 48,
        explanation: 'Secondary inspection recommended due to minor lighting reflection over date seal.',
        checks: [
          { id: 'doc_info', title: 'Document information valid', status: 'passed', detail: 'Visa metadata match' },
          { id: 'mrz', title: 'MRZ valid', status: 'passed', detail: 'Checksum valid' },
          { id: 'face', title: 'Face matched', status: 'passed', detail: 'Match score 89%' },
          { id: 'tamper', title: 'Minor edge anomaly', status: 'warning', detail: 'Glare reflection detected' },
        ],
        timestamp: 'Yesterday',
      },
      extractedFields: {
        visaNumber: { key: 'visaNumber', label: 'Visa Number', value: 'V98765432', confidence: 99 },
        visaType: { key: 'visaType', label: 'Visa Type', value: 'Tourist / Business', confidence: 97 },
      },
      savedPaths: { front: 'image/visa_front.svg' },
    },
    {
      id: 'scan-004',
      documentType: 'aadhaar',
      fileName: 'aadhaar_001',
      holderName: 'Rahul Sharma',
      identifier: 'XXXX XXXX 7821',
      riskLevel: 'LOW',
      riskScore: 18,
      timeAgo: 'Yesterday',
      timestamp: Date.now() - 90000000,
      imageThumbnail: '/samples/aadhaar_front.svg',
      backThumbnail: '/samples/aadhaar_back.svg',
      ekycVerified: true,
      result: {
        riskLevel: 'LOW RISK',
        riskScore: 18,
        explanation: 'Aadhaar eKYC fully authenticated. Front & Back demographics verified.',
        checks: [
          { id: 'doc_info', title: 'Document information valid', status: 'passed', detail: 'Valid UIDAI structure' },
          { id: 'mrz', title: 'QR signature valid', status: 'passed', detail: 'Cryptographic signature valid' },
          { id: 'face', title: 'Face matched', status: 'passed', detail: 'Match score 97%' },
          { id: 'ekyc', title: 'Aadhaar eKYC verified', status: 'passed', detail: 'Demographic attributes matched' },
        ],
        timestamp: 'Yesterday',
      },
      extractedFields: {
        name: { key: 'name', label: 'Name', value: 'Rahul Sharma', confidence: 99 },
        dateOfBirth: { key: 'dateOfBirth', label: 'Date of Birth', value: '14/03/2003', confidence: 97 },
        maskedAadhaar: { key: 'maskedAadhaar', label: 'Masked Aadhaar Number', value: 'XXXX XXXX 7821', confidence: 99 },
      },
      savedPaths: {
        front: 'image/aadhaar_front.svg',
        back: 'image/aadhaar_back.svg',
      },
    },
  ]);

  // 1. Multi-doc session completed from scanner
  const handleSessionComplete = (session: ScanSessionPayload) => {
    const primary = session.primaryDoc;

    // Store all session docs for gallery review
    setSessionDocs(session.documents);

    // Set primary doc as active document for downstream verification
    setRawImage(primary.rawImage);
    setProcessedImage(primary.processedImage);
    setSavedFilePaths({ front: primary.savedPath });

    // If there is a back-side doc for the same type, store it
    const backDoc = session.documents.find(
      (d) => d.docType === primary.docType && d.side === 'back'
    );
    if (backDoc) {
      setBackRawImage(backDoc.rawImage);
      setBackProcessedImage(backDoc.processedImage);
      setSavedFilePaths({ front: primary.savedPath, back: backDoc.savedPath });
    }

    setCorners(primary.corners);
    setDetectedType(primary.docType);
    setConfidence(primary.qualityScore || 97);
    setFileName(primary.fileName);
    setIsSuspicious(primary.isSuspicious);

    setStep('review');
  };

  // 2. Manual corner adjust confirm
  const handleManualCropConfirm = async (data: {
    points: Point[];
    horizontalTilt: number;
    verticalTilt: number;
  }) => {
    setCorners(data.points);
    const newProcessed = await processScanWithFallback(
      rawImage,
      data.points,
      data.horizontalTilt,
      data.verticalTilt
    );
    setProcessedImage(newProcessed);
    setStep('review');
  };

  // 3. Scan accepted -> Document details screen
  const handleAcceptScan = () => {
    setStep('doc-type');
  };

  // 4. Document checklist confirmed -> Run OCR on all scanned docs
  const handleDocTypeContinue = async (
    primaryDoc: DocumentType,
    name: string,
    unavailable: UnavailableDocFlags,
    checklist: DocChecklistEntry[]
  ) => {
    setDetectedType(primaryDoc);
    setFileName(name);
    setUnavailableDocs(unavailable);
    setSessionChecklist(checklist);

    // Run OCR for every doc marked as 'scanned'
    const scannedEntries = checklist.filter(e => e.status === 'scanned');
    const fieldsMap: Record<string, Record<string, ExtractedField>> = {};
    for (const entry of scannedEntries) {
      fieldsMap[entry.docType] = await ocr(
        processedImage || rawImage,
        entry.docType,
        isSuspicious
      );
    }
    setAllDocFields(fieldsMap);

    // Set primary doc fields for downstream verification
    setExtractedFields(fieldsMap[primaryDoc] || {});
    setStep('extract');
  };

  // 5. Extraction confirmed -> AI verification screen
  const handleProceedToVerification = (updatedFields: Record<string, ExtractedField>) => {
    setExtractedFields(updatedFields);
    setStep('verify');
  };

  // 6. Verification completed -> Either Aadhaar eKYC or Final Result
  const handleVerificationComplete = async () => {
    if (detectedType === 'aadhaar') {
      setStep('ekyc');
    } else {
      await generateFinalResult();
    }
  };

  // 7. Aadhaar eKYC completed
  const handleAadhaarEkycVerified = async (ekyc: AadhaarEkycData) => {
    setEkycData(ekyc);
    await generateFinalResult(ekyc);
  };

  // 7b. Aadhaar eKYC skipped
  const handleAadhaarEkycSkip = async () => {
    const skippedEkyc: AadhaarEkycData = {
      maskedAadhaar: extractedFields.maskedAadhaar?.value || 'XXXX XXXX 7821',
      nameVerified: false,
      dobVerified: false,
      genderVerified: false,
      isVerified: false,
      isSkipped: true,
      timestamp: new Date().toISOString(),
    };
    setEkycData(skippedEkyc);
    await generateFinalResult(skippedEkyc);
  };

  // Common final result calculation
  const generateFinalResult = async (ekyc?: AadhaarEkycData) => {
    const valResult = await validateDocument(detectedType, extractedFields, isSuspicious);
    const tampResult = await detectTampering(processedImage || rawImage, isSuspicious);
    const faceResult = await verifyFace(processedImage || rawImage, isSuspicious);

    const result = calculateRisk(
      detectedType,
      valResult,
      tampResult,
      faceResult,
      ekyc || ekycData
    );

    // Append N/A document notes into the audit checks
    const naEntries = (Object.entries(unavailableDocs) as [string, boolean][])
      .filter(([, isNA]) => isNA)
      .map(([type]) => ({
        id: `na_${type}`,
        title: `${type.replace('_', ' ')} not produced`,
        status: 'warning' as const,
        detail: 'Document not available — logged as N/A by officer',
      }));

    if (naEntries.length > 0) {
      result.checks = [...result.checks, ...naEntries];
    }

    setFinalResult(result);
    setStep('result');
  };

  // 8. Final Result Done button -> Save to history and reset to scanner
  const handleDone = () => {
    if (finalResult) {
      const newHistoryItem: HistoryItem = {
        id: `scan-${Date.now()}`,
        documentType: detectedType,
        fileName,
        holderName: extractedFields.name?.value || 'Rahul Sharma',
        identifier:
          extractedFields.passportNumber?.value ||
          extractedFields.maskedAadhaar?.value ||
          extractedFields.dlNumber?.value ||
          extractedFields.visaNumber?.value ||
          'ID-DOC-01',
        riskLevel:
          finalResult.riskLevel === 'LOW RISK'
            ? 'LOW'
            : finalResult.riskLevel === 'HIGH RISK'
            ? 'HIGH'
            : 'MEDIUM',
        riskScore: finalResult.riskScore,
        timeAgo: 'Just now',
        timestamp: Date.now(),
        imageThumbnail: processedImage || rawImage,
        backThumbnail: backProcessedImage || backRawImage,
        ekycVerified: ekycData?.isVerified || false,
        result: finalResult,
        extractedFields,
        savedPaths: savedFilePaths,
      };

      setHistory((prev) => [newHistoryItem, ...prev]);
    }

    // Reset workflow
    setRawImage('');
    setProcessedImage('');
    setBackRawImage(undefined);
    setBackProcessedImage(undefined);
    setCorners([]);
    setFinalResult(null);
    setEkycData(null);
    setUnavailableDocs({ aadhaar: false, driving_license: false, passport: false, visa: false });
    setStep('scanner');
  };

  // View past result from history
  const handleSelectHistoryRecord = (record: HistoryItem) => {
    setDetectedType(record.documentType);
    setFileName(record.fileName);
    setExtractedFields(record.extractedFields);
    setFinalResult(record.result);
    setActiveTab('scan');
    setStep('result');
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-0 sm:p-4">
      {/* Smartphone Container: Native CamScanner Smartphone Viewport */}
      <div className="smartphone-container relative rounded-none sm:rounded-[36px] overflow-hidden border-0 sm:border-8 sm:border-slate-800 shadow-2xl flex flex-col h-[100dvh] max-h-[100dvh] sm:h-[860px] sm:max-h-[860px]">
        {/* Main Content Area based on Tab & Step */}
        <div className="flex-1 overflow-hidden flex flex-col relative">
          {activeTab === 'scan' && (
            <>
              {step === 'scanner' && (
                <WebCamScanner
                  onSessionComplete={handleSessionComplete}
                  onRequestManualCrop={(img, c) => {
                    setRawImage(img);
                    setCorners(c);
                    setStep('crop');
                  }}
                />
              )}

              {step === 'crop' && (
                <ManualCropWrapper
                  imageSrc={rawImage}
                  initialCorners={corners}
                  onConfirmCrop={handleManualCropConfirm}
                  onCancel={() => setStep('scanner')}
                />
              )}

              {step === 'review' && (
                <ScanReviewScreen
                  scannedImage={processedImage || rawImage}
                  backImage={backProcessedImage || backRawImage}
                  savedFilePaths={savedFilePaths}
                  sessionDocs={sessionDocs}
                  onRetake={() => setStep('scanner')}
                  onAdjustCorners={() => setStep('crop')}
                  onAcceptScan={handleAcceptScan}
                />
              )}

              {step === 'doc-type' && (
                <DocumentTypeScreen
                  initialType={detectedType}
                  initialConfidence={confidence}
                  initialFileName={fileName}
                  onBack={() => setStep('review')}
                  onContinue={handleDocTypeContinue}
                />
              )}

              {step === 'extract' && (
                <ExtractionScreen
                  documentType={detectedType}
                  fileName={fileName}
                  documentImage={processedImage || rawImage}
                  backImage={backProcessedImage || backRawImage}
                  initialFields={extractedFields}
                  sessionChecklist={sessionChecklist}
                  allDocFields={allDocFields}
                  sessionDocs={sessionDocs}
                  onBack={() => setStep('doc-type')}
                  onProceedToVerification={handleProceedToVerification}
                />
              )}

              {step === 'verify' && (
                <VerificationScreen
                  documentType={detectedType}
                  isSuspicious={isSuspicious}
                  onComplete={handleVerificationComplete}
                />
              )}

              {step === 'ekyc' && (
                <AadhaarEkycScreen
                  maskedAadhaar={extractedFields.maskedAadhaar?.value || 'XXXX XXXX 7821'}
                  onBack={() => setStep('extract')}
                  onVerified={handleAadhaarEkycVerified}
                  onSkip={handleAadhaarEkycSkip}
                />
              )}

              {step === 'result' && finalResult && (
                <FinalResultScreen
                  documentType={detectedType}
                  fileName={fileName}
                  initialResult={finalResult}
                  onDone={handleDone}
                />
              )}
            </>
          )}

          {activeTab === 'history' && (
            <HistoryView
              history={history}
              onSelectRecord={handleSelectHistoryRecord}
              onStartNewScan={() => {
                setActiveTab('scan');
                setStep('scanner');
              }}
            />
          )}

          {activeTab === 'settings' && (
            <SettingsView
              onBackToScan={() => {
                setActiveTab('scan');
              }}
            />
          )}
        </div>

        {/* Bottom Smartphone Navigation: Minimal Tabs (Scan, History, Settings) */}
        <div className="h-14 bg-white border-t border-slate-200 flex items-center justify-around px-2 z-30 select-none flex-shrink-0">
          <button
            type="button"
            onClick={() => {
              setActiveTab('scan');
              if (step === 'result') setStep('scanner');
            }}
            className={`flex flex-col items-center justify-center gap-0.5 w-20 py-1 transition ${
              activeTab === 'scan'
                ? 'text-emerald-600 font-bold'
                : 'text-slate-400 hover:text-slate-600'
            }`}
          >
            <Camera className="w-5 h-5" />
            <span className="text-[10px]">Scan</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('history')}
            className={`flex flex-col items-center justify-center gap-0.5 w-20 py-1 transition ${
              activeTab === 'history'
                ? 'text-emerald-600 font-bold'
                : 'text-slate-400 hover:text-slate-600'
            }`}
          >
            <History className="w-5 h-5" />
            <span className="text-[10px]">History</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('settings')}
            className={`flex flex-col items-center justify-center gap-0.5 w-20 py-1 transition ${
              activeTab === 'settings'
                ? 'text-emerald-600 font-bold'
                : 'text-slate-400 hover:text-slate-600'
            }`}
          >
            <Settings className="w-5 h-5" />
            <span className="text-[10px]">Settings</span>
          </button>
        </div>
      </div>
    </div>
  );
}
