import { useState, useRef, useEffect } from 'react';
import { Box, styled, Button } from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import { useModel } from '../contexts/ModelContext';
import { Chat } from '../lib/types';
import { useSidebarStore } from '../lib/sidebarStore';
import ChatScreen from './ChatScreen';
import Sources from '../pages/Sources';
import { CustomHeader } from "./Header";
import { WelcomeFeatures } from './WelcomeFeatures';
import { Sidebar } from './Sidebar';
import { fetchLatestChat, resumeChat } from '../../src/lib/api';
import AddSource from '../../src/pages/AddSource';
import UpdateSource from '../pages/UpdateSource';

const MainContainer = styled(Box)(({ theme }) => ({
    minHeight: '100vh',
    backgroundColor: theme.palette.background.default,
    display: "flex",
    background: "#1a1a1a",
    color: "white",
    margin: 0,
    padding: 0,
    width: '100%',
    overflow: 'hidden',
}));

const Title = styled(Box)({
    fontSize: '22px',
    fontWeight: 50,
    fontFamily: 'Google Sans',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    '& .primary': {
        color: '#E3E3E3',
    },
    '& .gradient': {
        background: 'linear-gradient(to right, #4C8DF6, #FF0000)',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
    }
});

const Main = styled(Box, {
    shouldForwardProp: (prop) => prop !== "sidebarWidth" && prop !== "panelWidth",
})<{ sidebarWidth: number, panelWidth: number }>(({ sidebarWidth, panelWidth }) => ({
    transition: 'margin-left 0.3s ease-in-out',
    paddingTop: 0,
    paddingLeft: '0',
    paddingRight: '0',
    marginLeft: `${60 + panelWidth}px`,
    flexGrow: 1,
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    marginTop: 0,
    overflow: 'hidden',
    position: 'relative'
}));

// ChatPanel Component (as a placeholder - replace with your actual ChatPanel)
interface ChatPanelProps {
    onClose: () => void;
}

const ChatPanel: React.FC<ChatPanelProps> = ({ onClose }) => {
    return (
        <Box sx={{ position: 'fixed', top: '100px', right: '20px', border: '1px solid grey', background: 'white', padding: 2, zIndex: 100 }}>
            <div>Chat Content Goes Here</div>
            <Button onClick={onClose}>Close Chat</Button>
        </Box>
    );
};

export const MainApp = () => {
    const [currentChat, setCurrentChat] = useState<Chat | undefined>();
    const [showChat, setShowChat] = useState(false); // Lifted state (boolean for visibility)
    const [showWelcome, setShowWelcome] = useState(true);
    const [showSources, setShowSources] = useState(false);
    const [showAddSource, setShowAddSource] = useState(false);
    const [showEditSource, setShowEditSource] = useState(false);
    const [editSourceId, setEditSourceId] = useState<string | null>(null);
    const [chatScreenKey, setChatScreenKey] = useState(0); // NEW: Key for ChatScreen
    const [headerClicked, setHeaderClicked] = useState(false); // New state variable
    const [latestChat, setLatestChat] = useState<Chat | undefined>();
    const [isFileSelected, setIsFileSelected] = useState(false)

    const { isOpen, activePanel } = useSidebarStore();
    const { user } = useAuth();
    const { selectedModel } = useModel();

    const hasActivePanel = activePanel === 'history' || activePanel === 'settings';
    const sidebarWidth = isOpen ? 150 : 52;
    const panelWidth = hasActivePanel ? 300 : 0;

    const username = user?.displayName || 'User';

    const headerRef = useRef<HTMLDivElement>(null); // Ref for the header
    const [headerHeight, setHeaderHeight] = useState(0); // State for header's height

    useEffect(() => {
        const fetchLatest = async () => {
            if (user?.token && showChat && !currentChat) {
                const chat = await fetchLatestChat(user.token)();
                if (chat) {
                    setLatestChat(chat);
                } else {
                    setShowWelcome(true); // Fix: set showWelcome to true when no latest chat is found.
                }
            }
        };

        fetchLatest(); // Call the function
    }, [user, showChat, currentChat]);

    useEffect(() => {
        if (headerClicked) {
            handleNewChatFromHeader(); // Call the new function for header click
            setHeaderClicked(false);
            setShowSources(false);
            setShowAddSource(false);
            setShowEditSource(false);
        }
    }, [headerClicked]);
    console.log({
        showWelcome,
        showChat,
        currentChat,
        headerClicked,
        showSources,
        showAddSource,
        showEditSource,
    });

    useEffect(() => {
        setShowChat(true);
        setShowWelcome(true);
        setShowSources(false);
        setCurrentChat(undefined);
    }, []);

    useEffect(() => {
        const updateHeaderHeight = () => {
            if (headerRef.current) {
                setHeaderHeight(headerRef.current.clientHeight);  // Make sure to use clientHeight
            }
        };

        updateHeaderHeight();
        window.addEventListener('resize', updateHeaderHeight);
        return () => window.removeEventListener('resize', updateHeaderHeight);
    }, []);

    const handleHeaderClick = () => {
        setHeaderClicked(true); // Update the state when the header is clicked
    };

    const handleSelectChat = (chat: Chat) => {
        setCurrentChat(chat);
        setShowChat(true);
        setShowWelcome(false);
        setShowSources(false);
        setShowAddSource(false);  // Hide Add Source
        setShowEditSource(false); // Hide Edit Source
        if (chat.id === undefined) { // Check for new chat
            setChatScreenKey(prevKey => prevKey + 1); // Increment key for new chat
        }
    };

    const handleAddSourceClick = () => {
        console.log("Opening Add Source");
        setShowAddSource(true);
        setShowSources(false);
        setShowWelcome(false);
        setShowChat(false);
        setCurrentChat(undefined);
        setEditSourceId(null);
        setShowEditSource(false);
    };

    const handleChatStart = () => {
        console.log("In handleChatStart")
        setShowWelcome(false);
        setShowChat(true);
        setShowSources(false);
        setShowAddSource(false);  // Hide Add Source
        setShowEditSource(false); // Hide Edit Source
        setShowAddSource(false);  // Ensure Add Source is hidden
        setShowEditSource(false); // Ensure Edit Source is hidden
        setCurrentChat(undefined);
    };

    const handleEditClick = (sourceId: string) => {
        setEditSourceId(sourceId);
        setShowEditSource(true);
        setShowSources(false); // Hide Sources list when editing
        setShowWelcome(false);
        setShowChat(false);
    };

    const handleNewChat = () => {
        // Create a new empty chat object
        const newChat: Chat = {
            id: undefined,  // undefined for new chat
            title: 'New Chat',
            created_time: new Date().toISOString(),
            created_by: user?.uid || '',
            last_modified_time: new Date().toISOString(),
            last_modified_by: user?.uid || '',
            archived_at_timestamp: null,
            archived_by: '',
            deleted_at_timestamp: null,
            deleted_by: '',
            prompt: '',
            llm_type: selectedModel.id,
            user_id: user?.uid || '',
            agent_name: null,
            history: []
        };

        setCurrentChat(newChat); // Set the new chat object
        setShowChat(true);
        setShowWelcome(false);
        setShowSources(false);
        setShowAddSource(false);  // Ensure Add Source is hidden
        setShowEditSource(false); // Ensure Edit Source is hidden
        setChatScreenKey(prevKey => prevKey + 1); // Increment key also when handleNewChat is called directly
    };

    const handleNewChatFromHeader = () => {
        // Create a new empty chat object
        const newChat: Chat = {
            id: undefined,  // undefined for new chat
            title: 'New Chat',
            created_time: new Date().toISOString(),
            created_by: user?.uid || '',
            last_modified_time: new Date().toISOString(),
            last_modified_by: user?.uid || '',
            archived_at_timestamp: null,
            archived_by: '',
            deleted_at_timestamp: null,
            deleted_by: '',
            prompt: '',
            llm_type: selectedModel.id,
            user_id: user?.uid || '',
            agent_name: null,
            history: []
        };

        setCurrentChat(newChat); // Set the new chat object
        setShowChat(true); // Keep showChat as true to render ChatScreen
        setShowWelcome(true);
        setShowSources(false);
        setShowAddSource(false);  // Ensure Add Source is hidden
        setShowEditSource(false); // Ensure Edit Source is hidden
        setChatScreenKey(prevKey => prevKey + 1); // *Increment key for a fresh ChatScreen
    };

    const handleResumeChat = () => {
        setCurrentChat(latestChat)
    }

    return (
        <MainContainer>
            <Sidebar
                setShowChat={setShowChat}
                onSelectChat={(chat) => {
                    handleSelectChat(chat);
                    setShowAddSource(false);  // Hide Add Source when selecting a chat
                    setShowEditSource(false); // Hide Edit Source when selecting a chat
                }}
                selectedChatId={currentChat?.id}
                setShowSources={setShowSources}
                setShowWelcome={setShowWelcome}
                onNewChat={handleNewChat}
                onResumeChat={handleResumeChat}
                setShowAddSource={setShowAddSource}
                setShowEditSource={setShowEditSource}
                currentChat={currentChat}
            />
            <CustomHeader
                ref={headerRef}
                sidebarWidth={sidebarWidth}
                panelWidth={panelWidth}
                onTitleClick={() => {
                    handleHeaderClick(); // Just trigger the header click state
                }}
                title={
                    <Title >
                        <span className="primary">GenAI</span>
                        <span className="gradient">for Public Sector</span>
                    </Title>
                }
            />
            <Main sidebarWidth={sidebarWidth} panelWidth={panelWidth} sx={{ paddingTop: `${headerHeight}px` }}>
                {showWelcome && (
                    <Box sx={{
                        display: 'flex',
                        flexDirection: 'column',
                        width: '100%',
                        height: 'calc(100vh - 64px)',
                        justifyContent: 'center',
                        alignItems: 'center',
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        zIndex: 10,
                        paddingBottom: "150px", // added padding to create space for input
                        boxSizing: "border-box" // added to ensure padding does not add to size
                    }}>
                        <WelcomeFeatures
                            username={username}
                            headerHeight={headerHeight}
                            setShowChat={setShowChat}
                            setShowSources={setShowSources}
                            setShowWelcome={setShowWelcome}
                            onNewChat={handleNewChat}
                            onResumeChat={handleResumeChat}
                            setShowAddSource={setShowAddSource}
                            setShowEditSource={setShowEditSource}
                            onChatStart={() => {
                                handleChatStart();
                            }}
                            onSourcesView={() => {
                                setShowSources(true);
                                setShowWelcome(false);
                                setShowChat(false);
                            }}
                        />
                    </Box>
                )}
                {showChat && (
                    <ChatScreen
                        key={chatScreenKey} // NEW: Pass key prop to ChatScreen
                        currentChat={currentChat}
                        hideHeader={showWelcome || !currentChat} //Always show header
                        isNewChat={!currentChat}
                        onChatStart={() => {
                            handleChatStart();
                        }}
                        showWelcome={showWelcome} // pass show Welcome
                    />
                )}
                {showSources && !showAddSource && !showEditSource && <Sources onAddSourceClick={() => setShowAddSource(true)} onEditClick={handleEditClick} />}
                {showAddSource && <AddSource onCancel={() => { setShowAddSource(false); setShowSources(true); }} />}
                {showEditSource && (
                    <UpdateSource
                        sourceId={editSourceId!} // Pass the sourceId
                        onCancel={() => { setShowEditSource(false); setShowSources(true); }} // Hide UpdateSource and show Sources
                        onSave={() => { /* handle save logic here */ setShowEditSource(false); setShowSources(true); }}
                    />
                )}
            </Main>
        </MainContainer>
    );
};

export default MainApp;