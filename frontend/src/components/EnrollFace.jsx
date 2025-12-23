import React, { useRef, useState, useCallback } from 'react';
import {
  Box,
  Button,
  TextField,
  Typography,
  Card,
  CardContent,
  LinearProgress,
  Alert,
  Grid
} from '@mui/material';
import Webcam from 'react-webcam';
import * as faceapi from 'face-api.js';
import axios from 'axios';

const EnrollFace = ({ modelsLoaded }) => {
  const webcamRef = useRef(null);
  const canvasRef = useRef(null);
  const [personName, setPersonName] = useState('');
  const [isCapturing, setIsCapturing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('');
  const [faces, setFaces] = useState([]);

  const captureFrame = useCallback(async () => {
    if (!webcamRef.current || !modelsLoaded) return null;

    const video = webcamRef.current.video;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    const detection = await faceapi
      .detectSingleFace(video, new faceapi.TinyFaceDetectorOptions())
      .withFaceLandmarks()
      .withFaceDescriptor();

    if (detection) {
      const faceImage = faceapi.createCanvasFromMedia(video);
      faceapi.draw.drawDetections(faceImage, [detection.detection]);
      return {
        descriptor: detection.descriptor,
        imageData: faceImage.toDataURL('image/jpeg', 0.8)
      };
    }

    return null;
  }, [modelsLoaded]);

  const handleEnroll = async () => {
    if (!personName.trim()) {
      setStatus('Please enter a name');
      return;
    }

    if (!modelsLoaded) {
      setStatus('Face recognition models not loaded yet');
      return;
    }

    setIsCapturing(true);
    setProgress(0);
    setStatus('Starting enrollment...');
    setFaces([]);

    const collectedFaces = [];
    const targetFrames = 15;

    for (let i = 0; i < targetFrames; i++) {
      setStatus(`Capturing frame ${i + 1}/${targetFrames}...`);

      const frameData = await captureFrame();
      if (frameData) {
        collectedFaces.push(frameData.descriptor);
        setFaces(prev => [...prev, frameData.imageData]);
      }

      setProgress(((i + 1) / targetFrames) * 100);
      await new Promise(resolve => setTimeout(resolve, 200));
    }

    if (collectedFaces.length < targetFrames * 0.7) {
      setStatus('Insufficient face data captured. Try again.');
      setIsCapturing(false);
      return;
    }

    // Average the face descriptors
    const avgDescriptor = new Float32Array(128);
    collectedFaces.forEach(descriptor => {
      for (let j = 0; j < 128; j++) {
        avgDescriptor[j] += descriptor[j];
      }
    });
    for (let j = 0; j < 128; j++) {
      avgDescriptor[j] /= collectedFaces.length;
    }

    // Create hash for privacy
    const hashBuffer = await crypto.subtle.digest('SHA-256', avgDescriptor);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const encodingHash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

    try {
      await axios.post('/api/enroll', {
        name: personName.trim(),
        encodingHash: encodingHash
      });

      setStatus(`Successfully enrolled ${personName}!`);
      setPersonName('');
      setFaces([]);
    } catch (error) {
      setStatus('Enrollment failed. Please try again.');
      console.error('Enrollment error:', error);
    }

    setIsCapturing(false);
    setProgress(0);
  };

  const videoConstraints = {
    width: 640,
    height: 480,
    facingMode: 'user'
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Enroll Face
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
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
                  screenshotFormat="image/jpeg"
                  style={{
                    width: '100%',
                    height: 'auto',
                    borderRadius: 8
                  }}
                />
                <canvas
                  ref={canvasRef}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%'
                  }}
                />
              </Box>

              <Box sx={{ mt: 2 }}>
                <TextField
                  fullWidth
                  label="Person Name"
                  value={personName}
                  onChange={(e) => setPersonName(e.target.value)}
                  disabled={isCapturing}
                  sx={{ mb: 2 }}
                />

                <Button
                  variant="contained"
                  onClick={handleEnroll}
                  disabled={isCapturing || !modelsLoaded}
                  fullWidth
                >
                  {isCapturing ? 'Capturing...' : 'Start Enrollment'}
                </Button>

                {isCapturing && (
                  <LinearProgress
                    variant="determinate"
                    value={progress}
                    sx={{ mt: 2 }}
                  />
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Captured Faces
              </Typography>

              {faces.length > 0 ? (
                <Grid container spacing={1}>
                  {faces.map((faceData, index) => (
                    <Grid item xs={3} key={index}>
                      <img
                        src={faceData}
                        alt={`Face ${index + 1}`}
                        style={{
                          width: '100%',
                          height: 'auto',
                          borderRadius: 4
                        }}
                      />
                    </Grid>
                  ))}
                </Grid>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No faces captured yet
                </Typography>
              )}

              {status && (
                <Alert
                  severity={status.includes('Successfully') ? 'success' : 'info'}
                  sx={{ mt: 2 }}
                >
                  {status}
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default EnrollFace;
