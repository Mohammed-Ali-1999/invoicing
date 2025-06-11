import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Alert,
  Stack
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import axios from 'axios';

function ReconciliationResults({ setLoading, setError }) {
  const [results, setResults] = useState(null);

  const fetchResults = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await axios.get('http://localhost:5000/reconciliation-results');
      setResults(response.data);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to fetch reconciliation results');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const response = await axios.get('http://localhost:5000/export-reconciliation', {
        responseType: 'blob'
      });
      
      // Create a download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'reconciliation_results.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to export results');
    }
  };

  useEffect(() => {
    fetchResults();
  }, []);

  const getStatusColor = (status) => {
    switch (status) {
      case 'Matched':
        return '#90EE90'; // Light green
      case 'Missing':
        return '#FFB6C1'; // Light red
      case 'Extra':
        return '#ADD8E6'; // Light blue
      case 'Discrepancy':
        return '#FFB6C1'; // Light red
      default:
        return 'inherit';
    }
  };

  if (!results) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography variant="h6" color="textSecondary">
          No reconciliation results available
        </Typography>
        <Button
          variant="contained"
          color="primary"
          onClick={fetchResults}
          sx={{ mt: 2 }}
        >
          Refresh Results
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h6">
          Reconciliation Results
        </Typography>
        <Stack direction="row" spacing={2}>
          <Button
            variant="contained"
            color="primary"
            startIcon={<DownloadIcon />}
            onClick={handleExport}
          >
            Export Results
          </Button>
          <Button
            variant="outlined"
            color="primary"
            onClick={fetchResults}
          >
            Refresh Results
          </Button>
        </Stack>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Invoice ID</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Expected Total</TableCell>
              <TableCell align="right">Extracted Total</TableCell>
              <TableCell align="right">Difference</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {results.map((row, index) => (
              <TableRow
                key={index}
                sx={{
                  backgroundColor: getStatusColor(row.Status),
                  '&:last-child td, &:last-child th': { border: 0 }
                }}
              >
                <TableCell component="th" scope="row">
                  {row['Invoice ID']}
                </TableCell>
                <TableCell>{row.Status}</TableCell>
                <TableCell align="right">{row['Expected Total']}</TableCell>
                <TableCell align="right">{row['Extracted Total']}</TableCell>
                <TableCell align="right">{row.Difference}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}

export default ReconciliationResults; 