import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  List,
  ListItem,
  ListItemText,
  Paper,
  CircularProgress,
  FormControlLabel,
  Switch,
  IconButton
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import DeleteIcon from '@mui/icons-material/Delete';
import axios from 'axios';

function InvoiceUpload({ setLoading, setError }) {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [appendMode, setAppendMode] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [processingStage, setProcessingStage] = useState('');

  useEffect(() => {
    fetchUploadedFiles();
  }, []);

  const fetchUploadedFiles = async () => {
    try {
      const response = await axios.get('http://localhost:5000/uploaded-invoices');
      setUploadedFiles(response.data);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to fetch uploaded files');
    }
  };

  const handleFileSelect = (event) => {
    const newFiles = Array.from(event.target.files);
    
    // Check for duplicates against already uploaded files
    const duplicates = newFiles.filter(newFile => 
      uploadedFiles.some(existingFile => 
        existingFile.name.toLowerCase() === newFile.name.toLowerCase()
      )
    );

    if (duplicates.length > 0) {
      const duplicateNames = duplicates.map(file => file.name).join(', ');
      setError(`Duplicate files detected: ${duplicateNames}. Please remove these files before uploading.`);
      // Clear the file input
      event.target.value = '';
      return;
    }

    setSelectedFiles(newFiles);
    setError(null);
  };

  const handleDeleteSelected = (index) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleDeleteUploaded = async (filename) => {
    try {
      await axios.delete(`http://localhost:5000/uploaded-invoices/${encodeURIComponent(filename)}`);
      fetchUploadedFiles(); // Refresh the list
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to delete file');
    }
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;

    // Double check for duplicates before upload
    const duplicates = selectedFiles.filter(newFile => 
      uploadedFiles.some(existingFile => 
        existingFile.name.toLowerCase() === newFile.name.toLowerCase()
      )
    );

    if (duplicates.length > 0) {
      const duplicateNames = duplicates.map(file => file.name).join(', ');
      setError(`Duplicate files detected: ${duplicateNames}. Please remove these files before uploading.`);
      return;
    }

    setIsUploading(true);
    setError(null);
    setProcessingStage('Preparing files...');

    const formData = new FormData();
    selectedFiles.forEach(file => {
      formData.append('invoices', file);
    });

    try {
      setProcessingStage('Uploading files...');
      const response = await axios.post(
        `http://localhost:5000/upload-invoices?append=${appendMode}`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      if (response.data.success) {
        setSelectedFiles([]);
        fetchUploadedFiles();
      } else {
        setError(response.data.error || 'Failed to upload files');
      }
    } catch (err) {
      console.error('Upload error:', err);
      setError(err.response?.data?.error || 'Failed to upload files');
    } finally {
      setIsUploading(false);
      setProcessingStage('');
    }
  };

  return (
    <Box>
      <Paper
        sx={{
          p: 3,
          mb: 3,
          border: '2px dashed #ccc',
          borderRadius: 2,
          textAlign: 'center',
          backgroundColor: '#fafafa'
        }}
      >
        <input
          type="file"
          multiple
          onChange={handleFileSelect}
          style={{ display: 'none' }}
          id="invoice-upload"
          accept=".pdf,.png,.jpg,.jpeg"
        />
        <label htmlFor="invoice-upload">
          <Button
            variant="contained"
            component="span"
            startIcon={<CloudUploadIcon />}
            disabled={isUploading}
          >
            Select Invoices
          </Button>
        </label>

        <FormControlLabel
          control={
            <Switch
              checked={appendMode}
              onChange={(e) => setAppendMode(e.target.checked)}
              disabled={isUploading}
            />
          }
          label="Add to existing files"
          sx={{ ml: 2 }}
        />

        {selectedFiles.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              Selected Files:
            </Typography>
            <List dense>
              {selectedFiles.map((file, index) => (
                <ListItem
                  key={index}
                  secondaryAction={
                    <IconButton 
                      edge="end" 
                      aria-label="delete"
                      onClick={() => handleDeleteSelected(index)}
                      disabled={isUploading}
                    >
                      <DeleteIcon />
                    </IconButton>
                  }
                >
                  <ListItemText
                    primary={file.name}
                    secondary={`${(file.size / 1024).toFixed(1)} KB`}
                  />
                </ListItem>
              ))}
            </List>
            <Button
              variant="contained"
              color="primary"
              onClick={handleUpload}
              disabled={isUploading}
              sx={{ mt: 2 }}
            >
              {appendMode ? 'Add and Process Files' : 'Upload and Process Files'}
            </Button>
          </Box>
        )}

        {isUploading && (
          <Box sx={{ mt: 3, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
            <CircularProgress size={60} />
            <Typography variant="h6">
              {processingStage}
            </Typography>
          </Box>
        )}
      </Paper>

      {uploadedFiles.length > 0 && (
        <Box>
          <Typography variant="h6" gutterBottom>
            Currently Uploaded Invoices:
          </Typography>
          <List>
            {uploadedFiles.map((file, index) => (
              <ListItem
                key={index}
                secondaryAction={
                  <IconButton 
                    edge="end" 
                    aria-label="delete"
                    onClick={() => handleDeleteUploaded(file.name)}
                    disabled={isUploading}
                  >
                    <DeleteIcon />
                  </IconButton>
                }
              >
                <ListItemText
                  primary={file.name}
                  secondary={`${(file.size / 1024).toFixed(1)} KB - Uploaded at ${new Date(file.uploaded_at * 1000).toLocaleString()}`}
                />
              </ListItem>
            ))}
          </List>
        </Box>
      )}
    </Box>
  );
}

export default InvoiceUpload; 