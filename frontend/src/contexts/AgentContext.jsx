import React, { createContext, useContext, useState } from 'react';

const AgentContext = createContext();

export function AgentProvider({ children }) {
  const [isAgentOpen, setIsAgentOpen] = useState(false);
  const [messages, setMessages] = useState([]);

  const toggleAgent = () => setIsAgentOpen(prev => !prev);
  const addMessage = (msg) => setMessages(prev => [...prev, msg]);
  const clearMessages = () => setMessages([]);

  return (
    <AgentContext.Provider value={{
      isAgentOpen,
      setIsAgentOpen,
      toggleAgent,
      messages,
      addMessage,
      clearMessages,
      setMessages
    }}>
      {children}
    </AgentContext.Provider>
  );
}

export function useAgent() {
  return useContext(AgentContext);
}
