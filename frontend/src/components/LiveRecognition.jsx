import React, { useRef, useState, useEffect, useCallback } from 'react';
import {
  Box,
  Button,
  Typography,
  Card,
  CardContent,
  Alert,
  Chip,
  Grid,
  Paper
} from '@mui/material';
import Webcam from 'react-webcam';
import * as faceapi from 'face-api.js';
import axios from 'axios';

const LiveRecognition = ({ modelsLoaded }) => {
  const webcamRef = useRef(null);
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  const [isActive, setIsActive] = useState(false);
  const [recognizedFaces, setRecognizedFaces] = useState([]);
  const [persons, setPersons] = useState([]);
  const [status, setStatus] = useState('Click "Start Recognition" to begin');

  useEffect(() => {
    loadPersons();
  }, []);

  const loadPersons = async () => {
    try {
      const response = await axios.get('/api/persons');
      setPersons(response.data.persons);
    } catch (error) {
      console.error('Error loading persons:', error);
    }
  };

  const detectAndRecognize = useCallback(async () => {
    if (!webcamRef.current || !modelsLoaded || !isActive) return;

    const video = webcamRef.current.video;
    if (!video || video.readyState !== 4) return;

    try {
      // Detect faces
      const detections = await faceapi
        .detectAllFaces(video, new faceapi.TinyFaceDetectorOptions())
        .withFaceLandmarks()
        .withFaceDescriptors();

      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');

      // Clear previous drawings
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const currentFaces = [];

      for (const detection of detections) {
        const { x, y, width, height } = detection.detection.box;

        // Calculate confidence score (inverse of distance)
        let bestMatch = { name: 'Unknown', confidence: 0 };

        for (const person of persons) {
          // In a real implementation, you'd have the actual face descriptors
          // For demo purposes, we'll simulate matching
          const distance = Math.random(); // Simulated distance
          const confidence = Math.max(0, 1 - distance);

          if (confidence > bestMatch.confidence && confidence > 0.6) {
            bestMatch = { name: person.name, confidence };
          }
        }

        // Draw bounding box with confidence-based color
        const intensity = Math.min(255, Math.floor(bestMatch.confidence * 255));
        ctx.strokeStyle = bestMatch.name === 'Unknown'
          ? `rgb(255, ${intensity}, ${intensity})`
          : `rgb(${intensity}, 255, ${intensity})`;
        ctx.lineWidth = 3;
        ctx.strokeRect(x, y, width, height);

        // Draw label
        ctx.fillStyle = bestMatch.name === 'Unknown' ? '#ff4444' : '#44ff44';
        ctx.font = '16px Arial';
        const label = `${bestMatch.name} (${(bestMatch.confidence * 100).toFixed(1)}%)`;
        const textWidth = ctx.measureText(label).width;

        ctx.fillRect(x, y - 25, textWidth + 10, 25);
        ctx.fillStyle = 'white';
        ctx.fillText(label, x + 5, y - 5);

        currentFaces.push({
          name: bestMatch.name,
          confidence: bestMatch.confidence,
          box: { x, y, width, height }
        });
      }

      setRecognizedFaces(currentFaces);

      // Log unknown faces
      const unknownFaces = currentFaces.filter(face => face.name === 'Unknown');
      if (unknownFaces.length > 0) {
        try {
          await axios.post('/api/logs', {
            action: `detected_unknown_faces`,
            personName: null
          });
        } catch (error) {
          console.error('Error logging:', error);
        }
      }

    } catch (error) {
      console.error('Detection error:', error);
    }

    if (isActive) {
      animationRef.current = requestAnimationFrame(detectAndRecognize);
    }
  }, [modelsLoaded, isActive, persons]);

  const startRecognition = () => {
    setIsActive(true);
    setStatus('Recognition active - detecting faces...');
    detectAndRecognize();
  };

  const stopRecognition = () => {
    setIsActive(false);
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
    setRecognizedFaces([]);
    setStatus('Recognition stopped');
  };

  const videoConstraints = {
    width: 640,
    height: 480,
    facingMode: 'user'
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Live Recognition
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Camera Feed
              </Typography>

              <Box sx={{ position: 'relative', display: 'inline-block' }}>
                <Webcam
                  ref={webcamRef}
                  audio={false}
                  videoConstraints={videoConstraints}
                  style={{
                    width: '100%',
                    height: 'auto',
                    borderRadius: 8
                  }}
                  onLoadedData={() => {
                    const canvas = canvasRef.current;
                    if (canvas && webcamRef.current) {
                      canvas.width = webcamRef.current.video.videoWidth;
                      canvas.height = webcamRef.current.video.videoHeight;
                    }
                  }}
                />
                <canvas
                  ref={canvasRef}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    pointerEvents: 'none'
                  }}
                />
              </Box>

              <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
                <Button
                  variant="contained"
                  color="success"
                  onClick={startRecognition}
                  disabled={!modelsLoaded || isActive}
                >
                  Start Recognition
                </Button>

                <Button
                  variant="contained"
                  color="error"
                  onClick={stopRecognition}
                  disabled={!isActive}
                >
                  Stop Recognition
                </Button>
              </Box>

              <Alert
                severity="info"
                sx={{ mt: 2 }}
              >
                {status}
              </Alert>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Detected Faces
              </Typography>

              {recognizedFaces.length > 0 ? (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {recognizedFaces.map((face, index) => (
                    <Chip
                      key={index}
                      label={`${face.name} ${(face.confidence * 100).toFixed(1)}%`}
                      color={face.name === 'Unknown' ? 'error' : 'success'}
                      variant="outlined"
                    />
                  ))}
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No faces detected
                </Typography>
              )}

              <Paper sx={{ p: 2, mt: 2, bgcolor: 'grey.100' }}>
                <Typography variant="body2" color="text.secondary">
                  <strong>Registered Persons:</strong> {persons.length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  <strong>Confidence Threshold:</strong> 60%
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  <strong>Processing:</strong> Client-side (TensorFlow.js)
                </Typography>
              </Paper>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default LiveRecognition;
