import React, { useState } from 'react';
import { 
  Container, 
  Paper, 
  Typography, 
  Box, 
  Tab, 
  Tabs,
  CircularProgress,
  Alert
} from '@mui/material';
import InvoiceUpload from './components/InvoiceUpload';
import StatementUpload from './components/StatementUpload';
import ReconciliationResults from './components/ReconciliationResults';

function TabPanel({ children, value, index }) {
  return (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

function App() {
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [reconciliationData, setReconciliationData] = useState(null);

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom align="center">
          Invoice Processing System
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Paper sx={{ width: '100%' }}>
          <Tabs
            value={tabValue}
            onChange={handleTabChange}
            indicatorColor="primary"
            textColor="primary"
            centered
          >
            <Tab label="Upload Invoices" />
            <Tab label="Upload Statement" />
            <Tab label="Reconciliation Results" />
          </Tabs>

          <TabPanel value={tabValue} index={0}>
            <InvoiceUpload 
              setLoading={setLoading} 
              setError={setError}
            />
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <StatementUpload 
              setLoading={setLoading} 
              setError={setError}
            />
          </TabPanel>

          <TabPanel value={tabValue} index={2}>
            <ReconciliationResults 
              data={reconciliationData}
              setLoading={setLoading}
              setError={setError}
            />
          </TabPanel>
        </Paper>

        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
            <CircularProgress />
          </Box>
        )}
      </Box>
    </Container>
  );
}

export default App; 