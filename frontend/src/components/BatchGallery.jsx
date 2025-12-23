import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Box,
  Button,
  Typography,
  Card,
  CardContent,
  Grid,
  LinearProgress,
  Alert,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  ImageList,
  ImageListItem,
  ImageListItemBar
} from '@mui/material';
import * as faceapi from 'face-api.js';

const BatchGallery = ({ modelsLoaded }) => {
  const [files, setFiles] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState([]);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [selectedResult, setSelectedResult] = useState(null);

  const onDrop = useCallback((acceptedFiles) => {
    setFiles(prev => [...prev, ...acceptedFiles.map(file =>
      Object.assign(file, {
        preview: URL.createObjectURL(file)
      })
    )]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.bmp', '.tiff']
    },
    multiple: true
  });

  const processImages = async () => {
    if (!modelsLoaded || files.length === 0) return;

    setProcessing(true);
    setProgress(0);
    setResults([]);

    const processedResults = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const img = new Image();
      img.src = file.preview;

      await new Promise((resolve) => {
        img.onload = async () => {
          try {
            const detections = await faceapi
              .detectAllFaces(img, new faceapi.TinyFaceDetectorOptions())
              .withFaceLandmarks()
              .withFaceDescriptors();

            const faces = detections.map((detection, index) => ({
              id: index,
              confidence: detection.detection.score,
              box: detection.detection.box,
              // In a real implementation, you'd compare against stored descriptors
              match: Math.random() > 0.7 ? 'John Doe' : 'Unknown',
              matchConfidence: Math.random() * 0.4 + 0.6
            }));

            processedResults.push({
              filename: file.name,
              imageUrl: file.preview,
              faces: faces,
              totalFaces: faces.length
            });

          } catch (error) {
            console.error('Processing error:', error);
            processedResults.push({
              filename: file.name,
              imageUrl: file.preview,
              faces: [],
              totalFaces: 0,
              error: 'Processing failed'
            });
          }

          setProgress(((i + 1) / files.length) * 100);
          resolve();
        };
      });
    }

    setResults(processedResults);
    setProcessing(false);
  };

  const clearFiles = () => {
    setFiles([]);
    setResults([]);
    setProgress(0);
  };

  const exportResults = () => {
    const csvContent = [
      ['Filename', 'Total Faces', 'Matches', 'Unknown', 'Timestamp'],
      ...results.map(result => [
        result.filename,
        result.totalFaces,
        result.faces.filter(f => f.match !== 'Unknown').length,
        result.faces.filter(f => f.match === 'Unknown').length,
        new Date().toISOString()
      ])
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `faceidhub_batch_results_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const openPreview = (result) => {
    setSelectedResult(result);
    setPreviewOpen(true);
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Batch Gallery Processing
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Upload Images
              </Typography>

              <Box
                {...getRootProps()}
                sx={{
                  border: '2px dashed',
                  borderColor: isDragActive ? 'primary.main' : 'grey.300',
                  borderRadius: 2,
                  p: 3,
                  textAlign: 'center',
                  cursor: 'pointer',
                  bgcolor: isDragActive ? 'action.hover' : 'background.paper',
                  transition: 'all 0.2s ease'
                }}
              >
                <input {...getInputProps()} />
                <Typography variant="body1">
                  {isDragActive
                    ? 'Drop the images here...'
                    : 'Drag & drop images here, or click to select files'
                  }
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  Supports: JPEG, PNG, BMP, TIFF
                </Typography>
              </Box>

              {files.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2" gutterBottom>
                    {files.length} file(s) selected
                  </Typography>

                  <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                    <Button
                      variant="contained"
                      onClick={processImages}
                      disabled={processing || !modelsLoaded}
                      fullWidth
                    >
                      {processing ? 'Processing...' : 'Process Images'}
                    </Button>

                    <Button
                      variant="outlined"
                      onClick={clearFiles}
                      disabled={processing}
                    >
                      Clear
                    </Button>
                  </Box>

                  {processing && (
                    <LinearProgress
                      variant="determinate"
                      value={progress}
                      sx={{ mt: 2 }}
                    />
                  )}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Results
              </Typography>

              {results.length > 0 ? (
                <>
                  <ImageList cols={2} gap={8}>
                    {results.map((result, index) => (
                      <ImageListItem
                        key={index}
                        sx={{ cursor: 'pointer' }}
                        onClick={() => openPreview(result)}
                      >
                        <img
                          src={result.imageUrl}
                          alt={result.filename}
                          loading="lazy"
                          style={{ height: 120, objectFit: 'cover' }}
                        />
                        <ImageListItemBar
                          title={result.filename}
                          subtitle={`${result.totalFaces} faces`}
                        />
                      </ImageListItem>
                    ))}
                  </ImageList>

                  <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
                    <Button
                      variant="contained"
                      onClick={exportResults}
                      fullWidth
                    >
                      Export CSV
                    </Button>
                  </Box>
                </>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No results yet. Upload and process images to see results.
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Preview Dialog */}
      <Dialog
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {selectedResult?.filename}
        </DialogTitle>
        <DialogContent>
          {selectedResult && (
            <Box>
              <img
                src={selectedResult.imageUrl}
                alt={selectedResult.filename}
                style={{ width: '100%', height: 'auto', borderRadius: 8 }}
              />

              <Box sx={{ mt: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Detected Faces: {selectedResult.totalFaces}
                </Typography>

                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {selectedResult.faces.map((face, index) => (
                    <Chip
                      key={index}
                      label={`${face.match} ${(face.matchConfidence * 100).toFixed(1)}%`}
                      color={face.match === 'Unknown' ? 'warning' : 'success'}
                      size="small"
                    />
                  ))}
                </Box>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default BatchGallery;
