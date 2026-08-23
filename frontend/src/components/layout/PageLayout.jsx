import React from 'react';
import Sidebar from './Sidebar';
import TopNav from './TopNav';
import GlobalAgentPanel from '../GlobalAgentPanel';

const PageLayout = ({ children }) => {
  return (
    <div className="min-h-screen bg-dark-bg text-text-primary font-sans flex overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        <TopNav />
        <main className="flex-1 ml-20 md:ml-24 p-6 overflow-x-hidden overflow-y-auto no-scrollbar relative">
          {children}
        </main>
      </div>
      <GlobalAgentPanel />
    </div>
  );
};

export default PageLayout;
