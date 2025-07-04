import { useState, useEffect } from 'react';
import { Box, Button, Menu, MenuItem, Typography, CircularProgress } from '@mui/material';
import { ChevronDown, Search, Check } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { fetchAllEngines, fetchAllEngineJobs } from '../lib/api';
import { QueryEngine } from '../lib/types';

interface SourceSelectorProps {
    className?: string;
    chatId?: string;
    onSelectSource: (source: QueryEngine) => void;
    disabled?: boolean;
}

//Dummy source for Default-Chat to add to sources array 
const defaultChatSource: QueryEngine = {
    id: 'default-chat',
    name: 'Default Chat',
    description: 'Default chat without specific source',
    archived_at_timestamp: null,
    archived_by: '',
    created_by: '',
    created_time: new Date().toISOString(),
    deleted_at_timestamp: null,
    deleted_by: '',
    last_modified_by: '',
    last_modified_time: new Date().toISOString(),
    llm_type: null,
    parent_engine_id: '',
    user_id: 'default-user',
    query_engine_type: 'default_chat_type',
    embedding_type: 'default',
    vector_store: null,
    is_public: false,
    index_id: null,
    index_name: null,
    endpoint: null,
    doc_url: null,
    manifest_url: null,
    params: {
        is_multimodal: 'false',
    },
    depth_limit: 3,
    chunk_size: 1024,
    agents: [],
    child_engines: [],
    is_multimodal: false,
};

export function SourceSelector({ className, chatId, onSelectSource, disabled = false }: SourceSelectorProps) {
    const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
    const [selectedSource, setSelectedSource] = useState<QueryEngine | null>(defaultChatSource);
    const open = Boolean(anchorEl);
    const { user } = useAuth();
    const [sources, setSources] = useState<QueryEngine[]>([defaultChatSource]); // Initialize with Default Chat
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const handleClick = (event: React.MouseEvent<HTMLElement>) => {
        if (!disabled) {
            setAnchorEl(event.currentTarget);
        }
    };

    const handleClose = () => {
        setAnchorEl(null);
    };

    const handleSourceSelect = (source: QueryEngine) => {
        setSelectedSource(source);
        onSelectSource(source);
        handleClose();
    };

    useEffect(() => {
        const loadSources = async () => {
            if (!user?.token) return;

            try {
                setLoading(true);
                setError(null);
                const fetchedSources = await fetchAllEngines(user.token)();
                let allSources = [defaultChatSource]; // Start with Default Chat
                if (fetchedSources) {
                    // Fetch engine jobs to get status of each engine source
                    const engineJobs = await fetchAllEngineJobs(user.token)();
                    // Create a set of engine names that are active based on engine jobs
                    const activeEngineNames = new Set<string>();
                    if (engineJobs) {
                        engineJobs.forEach(job => {
                            if (job.status === 'active' && job.input_data?.query_engine) {
                                activeEngineNames.add(job.input_data.query_engine);
                            }
                        });
                    }
                    // Filter out fetchedSources that have a matching active engine job
                    const filteredSources = fetchedSources.filter(source => !activeEngineNames.has(source.name));
                    allSources = [defaultChatSource, ...filteredSources]; // Prepend Default Chat
                }
                setSources(allSources);
            } catch (err) {
                setError("Failed to load sources");
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        loadSources();
    }, [user]);

    useEffect(() => {
        if (chatId && sources.length > 0) {
            setSelectedSource(sources[0]);
        }
    }, [chatId, sources]);

    return (
        <Box className={className}>
            <Button
                onClick={handleClick}
                endIcon={<ChevronDown className="h-4 w-4" />}
                disabled={disabled || loading}
                sx={{
                    color: '#fff',
                    textTransform: 'none',
                    fontSize: '0.875rem',
                    padding: '6px 12px',
                    minWidth: '200px',
                    justifyContent: 'space-between',
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                    '&:hover': {
                        backgroundColor: disabled ? 'rgba(255, 255, 255, 0.1)' : 'rgba(255, 255, 255, 0.15)',
                    },
                    '&.Mui-disabled': {
                        color: 'rgba(255, 255, 255, 0.5)',
                    }
                }}
            >
                {loading ? (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <CircularProgress size={16} sx={{ color: 'inherit' }} />
                        <span>Loading sources...</span>
                    </Box>
                ) : selectedSource?.id == defaultChatSource.id ? "Select Source" : selectedSource ? selectedSource.name : "Select Source"}
            </Button>
            <Menu
                anchorEl={anchorEl}
                open={open}
                onClose={handleClose}
                PaperProps={{
                    sx: {
                        width: '250px',
                        maxHeight: '400px',
                        backgroundColor: '#2A2A2A',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        borderRadius: '8px',
                        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
                        '.MuiMenu-list': {
                            padding: '4px',
                        },
                    },
                }}
            >
                {/* Selected Source with Checkmark */}
                {selectedSource && (
                    <MenuItem
                        sx={{
                            backgroundColor: '#2A2A2A',
                            borderRadius: '4px',
                            py: 1,
                            px: 1.5,
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            mb: 1,
                            '&:hover': { backgroundColor: 'rgba(255, 255, 255, 0.1)' },
                        }}
                        onClick={() => handleSourceSelect(defaultChatSource)} // Allow re-selecting Default Chat
                    >
                        <Typography
                            sx={{
                                color: '#fff',
                                fontSize: '0.875rem',
                            }}
                        >
                            {selectedSource.name}
                        </Typography>
                        <Check className="h-4 w-4 text-white" />
                    </MenuItem>
                )}

                {/* Sources Title with Search Icon */}
                <MenuItem
                    disabled
                    sx={{
                        py: 1,
                        px: 1.5,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1,
                        borderRadius: '4px',
                        '&:hover': { backgroundColor: 'rgba(255, 255, 255, 0.1)' },
                    }}
                >
                    <Search className="h-4 w-4 text-white/70" />
                    <Typography
                        sx={{
                            color: '#fff',
                            fontSize: '0.875rem',
                            fontWeight: 500,
                        }}
                    >
                        Sources
                    </Typography>
                </MenuItem>

                {/* Error State */}
                {error && (
                    <MenuItem
                        sx={{
                            color: '#ff6b6b',
                            py: 1,
                            px: 1.5,
                            borderRadius: '4px',
                            justifyContent: 'center',
                        }}
                    >
                        {error}
                    </MenuItem>
                )}

                {/* Loading State */}
                {loading && (
                    <MenuItem
                        sx={{
                            justifyContent: 'center',
                            py: 1,
                            px: 1.5,
                            borderRadius: '4px',
                        }}
                    >
                        <CircularProgress size={20} sx={{ color: '#fff' }} />
                    </MenuItem>
                )}

                {/* Sources List */}
                {!loading && !error && sources.length === 1 && sources[0] === defaultChatSource && ( // Condition for "No sources available" to be more precise
                    <MenuItem
                        sx={{
                            color: '#fff',
                            py: 1,
                            px: 1.5,
                            borderRadius: '4px',
                            justifyContent: 'center',
                        }}
                    >
                        No sources available
                    </MenuItem>
                )}

                {!loading && !error && sources.map((source) => (
                    source.id !== selectedSource?.id && ( // Exclude selected source from the list
                        <MenuItem
                            key={source.id}
                            onClick={() => handleSourceSelect(source)}
                            sx={{
                                color: '#fff',
                                fontSize: '0.875rem',
                                py: 1,
                                px: 1.5,
                                borderRadius: '4px',
                                '&:hover': { backgroundColor: 'rgba(255, 255, 255, 0.1)' },
                            }}
                        >
                            {source.name}
                        </MenuItem>
                    )
                ))}
            </Menu>
        </Box>
    );
}