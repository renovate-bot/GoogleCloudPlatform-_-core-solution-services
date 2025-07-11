import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { createQueryEngine, fetchAllEngines, fetchEmbeddingModels } from '../lib/api';
import { QUERY_ENGINE_TYPES, QUERY_ENGINE_DEFAULT_TYPE, QueryEngine, ChatModel } from '../lib/types';
import {
  Avatar,
  Menu,
  ListItemButton,
  Switch,
  ListItemIcon,
} from "@mui/material";
import {
  Box,
  Typography,
  TextField,
  Select,
  MenuItem,
  Button,
  IconButton,
  Collapse,
  Slider,
  Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, List, ListItem, ListItemText
} from '@mui/material';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ClearIcon from '@mui/icons-material/Clear';
import styled from '@emotion/styled';
import CloseIcon from '@mui/icons-material/Close';

const StyledSelect = styled(Select)({
  backgroundColor: '#242424',
  color: 'white',
  '& .MuiOutlinedInput-notchedOutline': { borderColor: '#333' },
  '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: '#444' },
});

const STYLED_WHITE = 'white';

const StyledSlider = styled(Slider)({
  color: '#4a90e2',
  '& .MuiSlider-rail': {
    backgroundColor: '#333',
  },
  '& .MuiSlider-track': {
    backgroundColor: '#4a90e2',
  },
  '& .MuiSlider-thumb': {
    backgroundColor: '#4a90e2',
  },
  '& .MuiSlider-mark': {
    backgroundColor: '#666',
  },
  '& .MuiSlider-markLabel': {
    color: '#888',
  },
});

const StyledMenuItem = styled(MenuItem)({
  backgroundColor: '#242424',
  color: 'white',
  '&:hover': {
    backgroundColor: '#333',
  },
  '&.Mui-selected': {
    backgroundColor: '#2a2a2a',
    '&:hover': {
      backgroundColor: '#333',
    }
  }
});

const AddSource = ({ onCancel }: { onCancel: () => void }) => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [sources, setSources] = useState<QueryEngine[]>([]);
  const [isConfirmationModalOpen, setIsConfirmationModalOpen] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [embeddingModels, setEmbeddingModels] = useState<ChatModel[]>([]);


  const [formData, setFormData] = useState<Partial<QueryEngine>>({
    name: '',
    description: '',
    query_engine_type: QUERY_ENGINE_DEFAULT_TYPE,
    doc_url: '',
    embedding_type: 'VertexAI-Embedding',
    vector_store: 'langchain_pgvector',
    depth_limit: 0,
    chunk_size: 500,
    is_multimodal: false
  });

  // Fetch embedding models when component mounts
  useEffect(() => {
    const loadEmbeddingModels = async () => {
      if (user?.token) {
        try {
          const models = await fetchEmbeddingModels(user.token)();
          if (models && models.length > 0) {
            setEmbeddingModels(models);
            // Set default embedding type to the first model's id if available
            if (models[0]?.id) {
              handleChange('embedding_type', models[0].id);
            }
          }
        } catch (err) {
          console.error("Error fetching embedding models:", err);
        }
      }
    };

    loadEmbeddingModels();
  }, [user?.token]);

  const handleChange = (field: keyof QueryEngine, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };
  const handleSubmit = async () => {
    if (!user?.token) {
      console.error("User token is missing.");
      return;
    }

    if (!formData.name || !formData.doc_url) {
      setError("Please fill in all required fields.");
      return;
    }

    if (!/^https?:\/\/|^gs:\/\//.test(formData.doc_url)) {
      setError("Invalid URL. Must start with https://, http://, or gs://");
      return;
    }
    // Open confirmation modal without starting the API request
    setIsConfirmationModalOpen(true);
    setError(null);
  };


  const handleConfirmSubmit = async () => {
    if (!user || !user.token) {
      console.error("User token is missing.");
      setError("User authentication required.");
      return;
    }
    setIsSubmitted(true);
    setLoading(true);

    try {
      const response = await createQueryEngine(user.token)(formData as QueryEngine);

      if (response) {
        // Refetch the sources after successful creation (Important!)
        const engines = await fetchAllEngines(user.token)();
        if (engines) {
          console.log("Sources refetched after creation:", engines);

        } else {
          console.error("Failed to refetch sources after creation.");
        }
        onCancel(); // Call onCancel to trigger state update in Main.tsx

      } else {
        console.error("API call did not return a response.");
        setError("Failed to create source.");
      }
    } catch (err: any) {
      console.error("Error creating source:", err);
      setError(err.message || "Failed to create source.");
    } finally {
      setLoading(false);
      setIsConfirmationModalOpen(false);
    }
    setIsConfirmationModalOpen(true);
  };

  const handleConfirmationModalClose = () => {
    setIsConfirmationModalOpen(false);
  };

  const handleDepthLimitChange = (_event: Event, newValue: number | number[]) => {
    handleChange('depth_limit', newValue as number);
  };

  const handleChunkSizeChange = (_event: Event, newValue: number | number[]) => {
    handleChange('chunk_size', newValue as number);
  };

  const handleSwitchChange = (event: React.ChangeEvent<HTMLInputElement>) => { // Function to handle switch toggle.
    handleChange('is_multimodal', event.target.checked)
  };

  return (
    <>
      <Box sx={{
        height: '100vh',
        overflow: 'auto', // Add this to make the whole page scrollable
        backgroundColor: '#1a1a1a',
        marginTop: '64px',
        color: 'white'
      }}>
        {/* Header */}
        <Box sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          p: 2,
          borderBottom: '1px solid #333'
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography
              component="span"
              sx={{ color: '#888', cursor: 'pointer' }}
              onClick={onCancel}
            >
              Sources
            </Typography>
            <NavigateNextIcon sx={{ color: '#888' }} />
            <Typography>Add New</Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              variant="text"
              onClick={onCancel}  //  Use the onCancel prop directly
              sx={{ color: 'white' }}
            >
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={handleSubmit}
              disabled={loading}
              sx={{
                backgroundColor: '#4a90e2',
                '&:hover': { backgroundColor: '#357abd' }
              }}
            >
              Save
            </Button>
          </Box>
        </Box>

        {/* Form Content */}
        <Box sx={{ p: 3, maxWidth: '800px', mx: 'auto' }}>
          <Box sx={{ mb: 4 }}>
            <Typography variant="caption" sx={{ color: '#888', mb: 1, display: 'block' }}>
              Name
            </Typography>
            <TextField
              fullWidth
              placeholder="Input"
              value={formData.name}
              onChange={(e) => { if (e.target.value.length <= 50) { handleChange('name', e.target.value) } }}
              required
              error={!formData.name}
              helperText={!formData.name ? "Required" : null}
              InputProps={{
                endAdornment: formData.name && (
                  <IconButton size="small" onClick={() => handleChange('name', '')}>
                    <ClearIcon fontSize="small" sx={{ color: "white" }} />
                  </IconButton>
                )
              }}
              sx={{
                '& .MuiOutlinedInput-root': { backgroundColor: '#242424', color: 'white', '& fieldset': { borderColor: '#333' }, '&:hover fieldset': { borderColor: '#444' } }
              }}
            />
            <Typography variant="caption" sx={{ color: '#888', mb: 1, display: 'block' }}>Name of the Query Engine (can include spaces). {formData.name?.length || 0}/50 characters left.</Typography>
          </Box>

          {/* Add Description Field Here */}
          <Box sx={{ mb: 4 }}>
            <Typography variant="caption" sx={{ color: '#888', mb: 1, display: 'block' }}>
              Description
            </Typography>
            <TextField
              fullWidth
              placeholder="Enter a brief description"
              value={formData.description}
              onChange={(e) => {
                if (e.target.value.length <= 75) {
                  handleChange('description', e.target.value);
                }
              }}
              InputProps={{
                endAdornment: (
                  <Typography sx={{ color: '#888', mr: 1 }}>
                    {formData.description?.length || 0}/75
                  </Typography>
                ),
              }}
              sx={{
                '& .MuiOutlinedInput-root': {
                  backgroundColor: '#242424',
                  color: 'white',
                  '& fieldset': { borderColor: '#333' },
                  '&:hover fieldset': { borderColor: '#444' },
                }
              }}
            />
            <Typography variant="caption" sx={{ color: '#888', mb: 1, display: 'block' }}>A brief description of this source. {formData.description?.length || 0}/75 characters left.</Typography>
          </Box>

          <Box sx={{ mb: 4 }}>
            <Typography variant="caption" sx={{ color: '#888', mb: 1, display: 'block' }}>
              Data URL
            </Typography>
            <TextField
              fullWidth
              placeholder="Input"
              value={formData.doc_url}
              onChange={(e) => handleChange('doc_url', e.target.value)}
              required
              error={!formData.doc_url || !/^https?:\/\/|^gs:\/\//.test(formData.doc_url)}
              helperText={
                !formData.doc_url
                  ? "Required"
                  : !/^https?:\/\/|^gs:\/\//.test(formData.doc_url)
                    ? "Invalid URL. Must start with https://, http://, or gs://"
                    : ""
              }
              InputProps={{
                endAdornment: formData.doc_url && (
                  <IconButton size="small" onClick={() => handleChange('doc_url', '')}>
                    <ClearIcon fontSize="small" sx={{ color: "white" }} />
                  </IconButton>
                )
              }}
              sx={{
                '& .MuiOutlinedInput-root': {
                  backgroundColor: '#242424',
                  color: 'white',
                  '& fieldset': { borderColor: '#333' },
                  '&:hover fieldset': { borderColor: '#444' },
                }
              }}
            />
            <Typography variant="caption" sx={{ color: '#888', mb: 1, display: 'block' }}>Enter a valid URL starting with https://, http://, or gs://.</Typography>

          </Box>

          {formData.doc_url && /^https?:\/\//.test(formData.doc_url.replace(/^gs:\/\//, '')) && (
            <Box sx={{ mb: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Typography variant="caption" sx={{ color: '#888' }}>
                  Depth Limit
                </Typography>
                <Typography variant="caption" sx={{ color: 'white' }}>
                  {formData.depth_limit}
                </Typography>
              </Box>
              <StyledSlider
                value={formData.depth_limit ?? undefined}
                onChange={handleDepthLimitChange}
                min={0}
                max={4}
                step={1}
                marks
                sx={{ mb: 4 }}

              />

            </Box>
          )}


          <Button
            onClick={() => setShowAdvanced(!showAdvanced)}
            startIcon={<ExpandMoreIcon sx={{ transform: showAdvanced ? 'rotate(180deg)' : 'none' }} />}
            sx={{ color: 'white', textTransform: 'none' }}
          >
            {showAdvanced ? 'Hide' : 'Show'} Advanced Settings
          </Button>

          <Collapse in={showAdvanced}>
            <Box sx={{ p: 3, maxWidth: '800px', mx: 'auto' }}>
              {/* ... (rest of the form fields) */}
              <Box sx={{ mb: 4, display: 'flex', flexDirection: 'column' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: "100%", justifyContent: "space-between" }}> {/* New Box for row*/}
                  <Box sx={{ flex: 1, display: "flex", flexDirection: "column" }}> {/* New Box for column Type label and select*/}
                    <Typography variant="caption" sx={{ color: '#888', mb: 1, display: 'block' }}>
                      Type
                    </Typography>
                    <Box sx={{ flex: 1 }}>
                      <StyledSelect
                        fullWidth
                        value={formData.query_engine_type}
                        onChange={(e) => handleChange('query_engine_type', e.target.value)}
                        required
                        MenuProps={{
                          PaperProps: {
                            sx: {
                              backgroundColor: '#242424',
                              border: '1px solid #333',
                              borderRadius: '4px',
                              boxShadow: '0 4px 8px rgba(0, 0, 0, 0.5)',
                              maxHeight: '300px',
                            }
                          }
                        }}
                      >
                        {Object.entries(QUERY_ENGINE_TYPES).map(([key, value]) => (
                          <StyledMenuItem key={key} value={key}>
                            {value}{key === QUERY_ENGINE_DEFAULT_TYPE ? ' (Default)' : ''}
                          </StyledMenuItem>
                        ))}
                      </StyledSelect>
                    </Box>
                    <Typography variant="caption" sx={{ color: '#888', mb: 1, display: 'block' }}>Select the type of query engine you want to use.</Typography>
                  </Box>
                  {/* Multimodal section */}
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexDirection: 'column' }}>
                    <Typography variant="caption" sx={{ color: '#888', mb: 1, display: 'block' }}>Multimodal</Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Switch checked={formData.is_multimodal || false} onChange={handleSwitchChange} color="primary" />
                      <Typography variant="body1" sx={{ color: (formData.is_multimodal) ? '#fff' : '#888', fontWeight: "bold" }}>
                        {formData.is_multimodal ? 'Enabled' : 'Disabled'}
                      </Typography>
                    </Box>
                  </Box>
                  {/* End of multimodal section */}
                </Box>
              </Box>

              <Box sx={{ display: 'flex', gap: 2, mb: 4 }}>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="caption" sx={{ color: '#888', mb: 1, display: 'block' }}>
                    Vector Store
                  </Typography>
                  <StyledSelect
                    fullWidth
                    value={formData.vector_store}
                    onChange={(e) => handleChange('vector_store', e.target.value)}
                    MenuProps={{
                      PaperProps: {
                        sx: {
                          backgroundColor: "#242424", // Background for dropdown menu
                        },
                      },
                    }}
                  >
                    <MenuItem value="matching_engine">Vertex Matching Engine</MenuItem>
                    <MenuItem value="langchain_pgvector">PG Vector</MenuItem>
                  </StyledSelect>
                </Box>

                <Box sx={{ flex: 1 }}>
                  <Typography variant="caption" sx={{ color: '#888', mb: 1, display: 'block' }}>
                    Embedding Type
                  </Typography>
                  <StyledSelect
                    fullWidth
                    value={formData.embedding_type}
                    onChange={(e) => handleChange('embedding_type', e.target.value)}
                    MenuProps={{
                      PaperProps: {
                        sx: {
                          backgroundColor: "#242424", // Background for dropdown menu
                        },
                      },
                    }}
                  >
                    {embeddingModels.length > 0 ? (
                      embeddingModels.map((model) => (
                        <MenuItem key={model.id} value={model.id}>
                          {model.name}
                        </MenuItem>
                      ))
                    ) : (
                      <MenuItem value="VertexAI-Embedding">Vertex AI Text Embeddings</MenuItem>
                    )}
                  </StyledSelect>
                </Box>
              </Box>

              <Box sx={{ mb: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="caption" sx={{ color: '#888' }}>
                    Chunk Size
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'white' }}>
                    {formData.chunk_size}
                  </Typography>
                </Box>
                <StyledSlider
                  value={typeof formData.chunk_size === 'number' ? formData.chunk_size : 500}
                  onChange={handleChunkSizeChange}
                  min={100}
                  max={1000}
                  step={100}
                  marks
                />
              </Box>

              <Box sx={{ mb: 3 }}>
                <Typography variant="caption" sx={{ color: '#888', mb: 1, display: 'block' }}>
                  Agents
                </Typography>
                <TextField
                  fullWidth
                  placeholder="Placeholder"
                  value={formData.agents?.join(', ') || ''}
                  onChange={(e) => handleChange('agents', e.target.value.split(','))}
                  InputProps={{
                    endAdornment: formData.agents?.length ? (
                      <IconButton size="small" onClick={() => handleChange('agents', [])}>
                        <ClearIcon fontSize="small" sx={{ color: "white" }} />
                      </IconButton>
                    ) : null
                  }}
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      backgroundColor: '#242424',
                      color: 'white',
                      '& fieldset': { borderColor: '#333' },
                      '&:hover fieldset': { borderColor: '#444' },
                    }
                  }}
                />
              </Box>

              <Box sx={{ mb: 3 }}>
                <Typography variant="caption" sx={{ color: '#888', mb: 1, display: 'block' }}>
                  Child Sources
                </Typography>
                <TextField
                  fullWidth
                  placeholder="Placeholder"
                  value={formData.child_engines?.join(', ') || ''}
                  onChange={(e) => handleChange('child_engines', e.target.value.split(','))}
                  InputProps={{
                    endAdornment: formData.child_engines?.length ? (
                      <IconButton size="small" onClick={() => handleChange('child_engines', [])}>
                        <ClearIcon fontSize="small" sx={{ color: "white" }} />
                      </IconButton>
                    ) : null
                  }}
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      backgroundColor: '#242424',
                      color: 'white',
                      '& fieldset': { borderColor: '#333' },
                      '&:hover fieldset': { borderColor: '#444' },
                    }
                  }}
                />
              </Box>
            </Box>
          </Collapse>

          {error && (
            <Typography color="error" sx={{ mt: 2 }}>
              {error}
            </Typography>
          )}
        </Box>
        <Dialog open={isConfirmationModalOpen} onClose={handleConfirmationModalClose} PaperProps={{ sx: { width: '100%', maxWidth: '800px', backgroundColor: '#333537' } }}>
          <DialogTitle sx={{ color: STYLED_WHITE }}>Add New Source</DialogTitle>
          <IconButton
            onClick={handleConfirmationModalClose}
            sx={{ position: 'absolute', top: 8, right: 8 }}
          >
            <CloseIcon sx={{ color: STYLED_WHITE }} />
          </IconButton>
          <DialogContent sx={{ pt: 0 }}>
            <Typography variant="caption" sx={{ color: '#888', mb: 1, display: 'block' }}>
              Source Name:
            </Typography>
            <Typography variant="h6" sx={{ color: STYLED_WHITE, '& .MuiListItemText-secondary': { color: STYLED_WHITE }, borderBottom: '1px solid #888' }}>
              {formData.name}
            </Typography>
            <Typography variant="caption" sx={{ color: '#888', mb: 1, display: 'block', }}>Description:</Typography>
            <Typography sx={{ color: STYLED_WHITE, '& .MuiListItemText-secondary': { color: STYLED_WHITE } }}>
              {formData.description}
            </Typography>
            <Box sx={{ backgroundColor: '#242424', p: 2, mt: 2, borderRadius: 1 }}>
              <Typography sx={{ color: '#888', mb: 1, display: 'block' }}>These settings are not editable after adding this source</Typography>
            </Box>
            <List sx={{ color: STYLED_WHITE }}>
              <ListItem sx={{ borderBottom: '1px solid #888' }}>
                <ListItemText primary="Data URL:" secondary={formData?.doc_url} sx={{ color: STYLED_WHITE, '& .MuiListItemText-secondary': { color: STYLED_WHITE } }} />
              </ListItem>
              <ListItem sx={{ display: 'flex', alignItems: 'center', gap: 2, borderBottom: '1px solid #888' }}>
                <Box sx={{ flex: 1 }}>
                  <ListItemText primary="Type:" secondary={QUERY_ENGINE_TYPES[formData?.query_engine_type as keyof typeof QUERY_ENGINE_TYPES] || formData?.query_engine_type} sx={{ color: STYLED_WHITE, '& .MuiListItemText-secondary': { color: STYLED_WHITE } }} />
                </Box>
                <Box sx={{ flex: 1 }}>
                  <ListItemText primary="MultiModal:" secondary={formData?.is_multimodal ? "Enabled" : "Disabled"} sx={{ color: STYLED_WHITE, '& .MuiListItemText-secondary': { color: STYLED_WHITE } }} />
                </Box>
              </ListItem>
              <ListItem sx={{ display: 'flex', alignItems: 'center', gap: 2, borderBottom: '1px solid #888' }}>
                <Box sx={{ flex: 1 }}>
                  <ListItemText primary="Vector Store:" secondary={formData?.vector_store === 'langchain_pgvector' ? 'PG Vector' : 'Vertex Matching Engine'} sx={{ color: STYLED_WHITE, '& .MuiListItemText-secondary': { color: STYLED_WHITE } }} />
                </Box>
                <Box sx={{ flex: 1 }}>
                  <ListItemText
                    primary="Embedding Type:"
                    secondary={
                      formData.embedding_type
                        ? embeddingModels.find(model => model.id === formData?.embedding_type)?.name ||
                          formData?.embedding_type
                        : "N/A"
                    }
                    sx={{ color: STYLED_WHITE, '& .MuiListItemText-secondary': { color: STYLED_WHITE } }}
                  />
                </Box>
              </ListItem>
              <ListItem sx={{ display: 'flex', alignItems: 'center', gap: 2, borderBottom: '1px solid #888' }}>
                <Box sx={{ flex: 1 }}>
                  <ListItemText primary="Depth Limit:" secondary={formData?.depth_limit?.toString()} sx={{ color: STYLED_WHITE, '& .MuiListItemText-secondary': { color: STYLED_WHITE } }} />
                </Box>
                <Box sx={{ flex: 1 }}>
                  <ListItemText primary="Chunk Size:" secondary={formData?.chunk_size?.toString()} sx={{ color: STYLED_WHITE, '& .MuiListItemText-secondary': { color: STYLED_WHITE } }} />
                  </Box>
              </ListItem>
              <ListItem sx={{ display: 'flex', alignItems: 'center', gap: 2, borderBottom: '1px solid #888' }}>
                <ListItemText sx={{ color: formData.agents?.length ? STYLED_WHITE : '#888', '& .MuiListItemText-secondary': { color: formData.agents?.length ? STYLED_WHITE : '#888' } }} primary="Agents:" secondary={formData.agents?.join(", ") || 'N/A'} />
              </ListItem>
              <ListItem sx={{ display: 'flex', alignItems: 'center', gap: 2, borderBottom: '0px' }}>
                <ListItemText sx={{ color: formData.child_engines?.length ? STYLED_WHITE : '#888', '& .MuiListItemText-secondary': { color: formData.child_engines?.length ? STYLED_WHITE : '#888' } }} primary="Child Sources:" secondary={formData.child_engines?.join(", ") || 'N/A'} />
              </ListItem>
            </List>
          </DialogContent>
          <DialogActions>
            <ListItemButton onClick={() => { handleConfirmationModalClose(); setIsConfirmationModalOpen(false); }} sx={{ color: "#A8C7FA" }} >
              Continue Editing
            </ListItemButton>
            <Button onClick={handleConfirmSubmit} color="primary" variant="contained" sx={{
              borderRadius: '20px', textTransform: 'none', backgroundColor: '#A8C7FA', color: '#062E6F', '&:focus-visible': {
                boxShadow: '0 0 0 2px #4a90e2', /* Add focus-visible styles */
                border: '1px solid #4a90e2',
              },
            }}>
              Add New Source
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </>
  );
};

export default AddSource;
