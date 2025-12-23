import React, { useState, useEffect } from 'react';
import {
  ThemeProvider,
  createTheme,
  CssBaseline,
  Box,
  Tabs,
  Tab,
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Switch,
  FormControlLabel
} from '@mui/material';
import { Brightness4, Brightness7 } from '@mui/icons-material';
import * as faceapi from 'face-api.js';

import ConsentModal from './components/ConsentModal';
import EnrollFace from './components/EnrollFace';
import LiveRecognition from './components/LiveRecognition';
import BatchGallery from './components/BatchGallery';

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#90caf9',
    },
    secondary: {
      main: '#f48fb1',
    },
  },
});

const lightTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function App() {
  const [tabValue, setTabValue] = useState(0);
  const [darkMode, setDarkMode] = useState(false);
  const [consentGiven, setConsentGiven] = useState(false);
  const [modelsLoaded, setModelsLoaded] = useState(false);

  const theme = darkMode ? darkTheme : lightTheme;

  useEffect(() => {
    // Check for consent
    const consent = localStorage.getItem('faceidhub_consent');
    if (consent === 'accepted') {
      setConsentGiven(true);
    }

    // Load face-api.js models
    loadModels();
  }, []);

  const loadModels = async () => {
    try {
      await Promise.all([
        faceapi.nets.tinyFaceDetector.loadFromUri('/models'),
        faceapi.nets.faceLandmark68Net.loadFromUri('/models'),
        faceapi.nets.faceRecognitionNet.loadFromUri('/models'),
        faceapi.nets.ssdMobilenetv1.loadFromUri('/models')
      ]);
      setModelsLoaded(true);
      console.log('Face recognition models loaded');
    } catch (error) {
      console.error('Error loading models:', error);
    }
  };

  const handleConsentAccept = () => {
    localStorage.setItem('faceidhub_consent', 'accepted');
    setConsentGiven(true);
  };

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  if (!consentGiven) {
    return <ConsentModal onAccept={handleConsentAccept} />;
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ flexGrow: 1 }}>
        <AppBar position="static">
          <Toolbar>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              FaceIDHub
            </Typography>
            <FormControlLabel
              control={
                <Switch
                  checked={darkMode}
                  onChange={() => setDarkMode(!darkMode)}
                  icon={<Brightness7 />}
                  checkedIcon={<Brightness4 />}
                />
              }
              label=""
            />
          </Toolbar>
        </AppBar>

        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="face recognition tabs">
            <Tab label="Enroll Face" />
            <Tab label="Live Recognition" />
            <Tab label="Batch Gallery" />
          </Tabs>
        </Box>

        <Box sx={{ p: 3 }}>
          {!modelsLoaded && (
            <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
              Loading face recognition models...
            </Typography>
          )}

          {tabValue === 0 && <EnrollFace modelsLoaded={modelsLoaded} />}
          {tabValue === 1 && <LiveRecognition modelsLoaded={modelsLoaded} />}
          {tabValue === 2 && <BatchGallery modelsLoaded={modelsLoaded} />}
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App;
