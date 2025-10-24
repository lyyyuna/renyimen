const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  callClaude: (userInput) => ipcRenderer.invoke('call-claude', userInput),
  requestMicrophonePermission: () => ipcRenderer.invoke('request-microphone-permission'),
  checkMicrophonePermission: () => ipcRenderer.invoke('check-microphone-permission')
});
