const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  callClaude: (userInput) => ipcRenderer.invoke('call-claude', userInput)
});
