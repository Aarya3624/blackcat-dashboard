// const { app, BrowserWindow } = require('electron');
// const { exec, spawn } = require('child_process');
// const path = require('path');
// const kill = require('tree-kill');

// let mainWindow;
// let pythonProcess;
// let nextJsProcess;

// function createWindow() {
//   mainWindow = new BrowserWindow({
//     width: 1280,
//     height: 720,
//     webPreferences: {
//       contextIsolation: true,
//       preload: path.join(__dirname, 'preload.js')
//     }
//   });

//   mainWindow.loadURL('http://localhost:3000');

//   mainWindow.on('closed', () => {
//     mainWindow = null;
//   });
// }

// function startPythonScript() {
//   const scriptPath = path.join(__dirname, '../backend/people-counter/redoing.py');
//   pythonProcess = spawn('python', [scriptPath], { stdio: 'inherit' });

//   pythonProcess.on('error', (error) => {
//     console.error(`Error executing Python script: ${error.message}`);
//   });
// }

// function startNextJs() {
//   const nextJsPath = path.join(__dirname, '../src/app');
//   nextJsProcess = exec('npm run dev', { cwd: nextJsPath });

//   nextJsProcess.stdout.on('data', (data) => {
//     console.log(`Next.js output: ${data}`);
//   });

//   nextJsProcess.stderr.on('data', (data) => {
//     console.error(`Next.js stderr: ${data}`);
//   });

//   nextJsProcess.on('error', (error) => {
//     console.error(`Error starting Next.js: ${error.message}`);
//   });
// }

// function stopProcesses() {
//   if (pythonProcess) {
//     pythonProcess.kill('SIGINT');
//   }
//   if (nextJsProcess && nextJsProcess.pid) {
//     kill(nextJsProcess.pid, 'SIGINT', (err) => {
//       if (err) {
//         console.error(`Error killing Next.js process: ${err.message}`);
//       }
//     });
//   }
// }

// app.whenReady().then(() => {
//   startPythonScript();
//   startNextJs();
//   createWindow();

//   app.on('activate', () => {
//     if (BrowserWindow.getAllWindows().length === 0) {
//       createWindow();
//     }
//   });
// });

// app.on('window-all-closed', () => {
//   stopProcesses();
//   if (process.platform !== 'darwin') {
//     app.quit();
//   }
// });

// app.on('quit', () => {
//   stopProcesses();
// });

const { app, BrowserWindow } = require('electron');
const { exec } = require('child_process');
const path = require('path');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  // Load the Next.js frontend
  mainWindow.loadURL('http://localhost:3000');

  mainWindow.on('closed', function () {
    mainWindow = null;
  });
}

app.on('ready', () => {
  // Start the Python backend
  exec(path.join(__dirname, 'backend', 'backend.exe'), (err, stdout, stderr) => {
    if (err) {
      console.error(`Error starting Python backend: ${stderr}`);
      return;
    }
    console.log(`Backend output: ${stdout}`);
  });

  createWindow();
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
