import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Checkbox,
  FormControlLabel,
  Alert
} from '@mui/material';

const ConsentModal = ({ onAccept }) => {
  const [accepted, setAccepted] = useState(false);

  const handleAccept = () => {
    if (accepted) {
      onAccept();
    }
  };

  return (
    <Dialog
      open={true}
      maxWidth="md"
      fullWidth
      disableEscapeKeyDown
    >
      <DialogTitle>
        <Typography variant="h5" component="div">
          FaceIDHub Privacy Consent
        </Typography>
      </DialogTitle>

      <DialogContent>
        <Box sx={{ mb: 2 }}>
          <Alert severity="info" sx={{ mb: 2 }}>
            FaceIDHub processes all face recognition locally in your browser.
            No images or personal data are uploaded to external servers.
          </Alert>

          <Typography variant="h6" gutterBottom>
            Privacy Policy
          </Typography>

          <Typography variant="body1" paragraph>
            FaceIDHub is committed to protecting your privacy and follows these principles:
          </Typography>

          <Box component="ul" sx={{ pl: 3 }}>
            <Typography component="li" variant="body2" paragraph>
              ✓ All face processing happens locally in your browser using TensorFlow.js
            </Typography>
            <Typography component="li" variant="body2" paragraph>
              ✓ Face data is stored temporarily in browser memory only
            </Typography>
            <Typography component="li" variant="body2" paragraph>
              ✓ No images are uploaded to external servers
            </Typography>
            <Typography component="li" variant="body2" paragraph>
              ✓ You can clear all stored data at any time
            </Typography>
            <Typography component="li" variant="body2" paragraph>
              ✓ Face recognition may have biases based on training data diversity
            </Typography>
          </Box>

          <Typography variant="body2" color="text.secondary" sx={{ mt: 2, fontStyle: 'italic' }}>
            By continuing, you consent to local face processing for personal use only.
            Face recognition technology should be used responsibly and ethically.
          </Typography>
        </Box>

        <FormControlLabel
          control={
            <Checkbox
              checked={accepted}
              onChange={(e) => setAccepted(e.target.checked)}
              color="primary"
            />
          }
          label="I understand and accept the privacy policy"
        />
      </DialogContent>

      <DialogActions>
        <Button
          onClick={handleAccept}
          variant="contained"
          disabled={!accepted}
          size="large"
        >
          Continue to FaceIDHub
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ConsentModal;
