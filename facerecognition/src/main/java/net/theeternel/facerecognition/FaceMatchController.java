package net.theeternel.facerecognition;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import java.util.Map;
import java.util.HashMap;

@RestController
@RequestMapping("/api/face-match")
public class FaceMatchController {

    @PostMapping
    public ResponseEntity<Map<String, Object>> matchFaces(@RequestBody Map<String, String> payload) {
        String image1Path = payload.get("image1");
        String image2Path = payload.get("image2");
        
        Map<String, Object> response = new HashMap<>();
        
        if (image1Path == null || image2Path == null) {
            response.put("error", "Both image1 and image2 paths are required");
            return ResponseEntity.badRequest().body(response);
        }
        
        // Mock Face Recognition Logic
        // In a real scenario, this would use OpenCV/DL4J to compute embeddings and cosine similarity.
        // For this demo, we simulate a successful match if paths are provided.
        double score = 88.5 + (Math.random() * 10); // Random score between 88.5 and 98.5
        boolean matched = score > 90.0;
        
        response.put("matched", matched);
        response.put("score", score);
        response.put("image1", image1Path);
        response.put("image2", image2Path);
        
        return ResponseEntity.ok(response);
    }
}

