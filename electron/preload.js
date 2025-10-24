import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('electronAPI', {
  callClaude: (userInput) => ipcRenderer.invoke('call-claude', userInput)
});
