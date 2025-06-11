import React, { useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { 
  Box, 
  Typography, 
  Paper,
  Button,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow
} from '@mui/material';
import { 
  CloudUpload as CloudUploadIcon,
  Description as DescriptionIcon
} from '@mui/icons-material';
import axios from 'axios';

function StatementUpload({ setLoading, setError }) {
  const [file, setFile] = React.useState(null);
  const [uploadedStatement, setUploadedStatement] = React.useState(null);
  const [previewData, setPreviewData] = React.useState(null);

  const fetchUploadedStatement = async () => {
    try {
      const response = await axios.get('http://localhost:5000/uploaded-statement');
      setUploadedStatement(response.data);
      if (response.data) {
        fetchPreview();
      }
    } catch (err) {
      console.error('Failed to fetch uploaded statement:', err);
    }
  };

  const fetchPreview = async () => {
    try {
      const response = await axios.get('http://localhost:5000/statement-preview');
      setPreviewData(response.data);
    } catch (err) {
      console.error('Failed to fetch statement preview:', err);
    }
  };

  useEffect(() => {
    fetchUploadedStatement();
  }, []);

  const onDrop = useCallback(acceptedFiles => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv']
    },
    maxFiles: 1
  });

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a statement file to upload');
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('statement', file);

    try {
      const response = await axios.post('http://localhost:5000/upload-statement', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      if (response.data.success) {
        setFile(null);
        setError(null);
        fetchUploadedStatement(); // Refresh the uploaded statement info and preview
      } else {
        setError(response.data.error || 'Failed to process statement');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to upload statement');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Paper
        {...getRootProps()}
        sx={{
          p: 3,
          textAlign: 'center',
          cursor: 'pointer',
          backgroundColor: isDragActive ? '#f0f0f0' : 'white',
          border: '2px dashed #ccc',
          '&:hover': {
            backgroundColor: '#f0f0f0'
          }
        }}
      >
        <input {...getInputProps()} />
        <CloudUploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
        <Typography variant="h6" gutterBottom>
          {isDragActive
            ? 'Drop the statement file here...'
            : 'Drag and drop statement file here, or click to select file'}
        </Typography>
        <Typography variant="body2" color="textSecondary">
          Supported format: CSV
        </Typography>
      </Paper>

      {file && (
        <Box sx={{ mt: 3 }}>
          <Alert severity="info" sx={{ mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <DescriptionIcon sx={{ mr: 1 }} />
              <Typography>
                Selected file: {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
              </Typography>
            </Box>
          </Alert>

          <Box sx={{ textAlign: 'center' }}>
            <Button
              variant="contained"
              color="primary"
              onClick={handleUpload}
            >
              Upload and Process Statement
            </Button>
          </Box>
        </Box>
      )}

      {uploadedStatement && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="h6" gutterBottom>
            Currently Uploaded Statement:
          </Typography>
          <List>
            <ListItem>
              <ListItemIcon>
                <DescriptionIcon />
              </ListItemIcon>
              <ListItemText
                primary={uploadedStatement.name}
                secondary={`${(uploadedStatement.size / 1024 / 1024).toFixed(2)} MB - Uploaded ${new Date(uploadedStatement.uploaded_at * 1000).toLocaleString()}`}
              />
            </ListItem>
          </List>

          {previewData && previewData.headers && previewData.rows && (
            <Box sx={{ mt: 3 }}>
              <Typography variant="h6" gutterBottom>
                CSV Preview:
              </Typography>
              <TableContainer 
                component={Paper} 
                sx={{ 
                  maxHeight: 400,
                  '& .MuiTableHead-root': {
                    position: 'sticky',
                    top: 0,
                    backgroundColor: 'white',
                    zIndex: 1,
                    '& th': {
                      backgroundColor: 'white',
                      borderBottom: '2px solid rgba(224, 224, 224, 1)'
                    }
                  }
                }}
              >
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      {previewData.headers.map((header, index) => (
                        <TableCell key={index}>{header}</TableCell>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {previewData.rows.map((row, rowIndex) => (
                      <TableRow key={rowIndex}>
                        {row.map((cell, cellIndex) => (
                          <TableCell key={cellIndex}>{cell}</TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
              <Typography variant="caption" color="textSecondary" sx={{ mt: 1, display: 'block' }}>
                Showing {previewData.rows.length} rows
              </Typography>
            </Box>
          )}
        </Box>
      )}
    </Box>
  );
}

export default StatementUpload; 