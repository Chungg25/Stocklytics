import React from 'react';
import Sidebar from './Sidebar';
import TopNav from './TopNav';

const PageLayout = ({ children }) => {
  return (
    <div className="min-h-screen bg-dark-bg text-text-primary font-sans flex">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <TopNav />
        <main className="flex-1 ml-20 md:ml-24 p-6 overflow-x-hidden">
          {children}
        </main>
      </div>
    </div>
  );
};

export default PageLayout;
