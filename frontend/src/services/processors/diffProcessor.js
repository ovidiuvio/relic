import { decodeContent, getTextMetadata } from './utils/contentUtils';
import { highlightCode } from './codeProcessor.js';

/**
 * Process unified diff content
 */
export async function processDiff(content) {
  const text = decodeContent(content);
  const metadata = getTextMetadata(text);
  
  // Parse the diff into files and hunks
  const files = parseDiff(text);
  
  return {
    type: 'diff',
    preview: text, // Raw text for source view
    highlighted: await highlightCode(text, 'diff'),
    files,
    metadata: {
      ...metadata,
      language: 'diff'
    }
  };
}

function parseDiff(text) {
  const lines = text.split('\n');
  const files = [];
  let currentFile = null;
  let currentHunk = null;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    
    // File header: diff --git a/file b/file or --- a/file +++ b/file
    if (line.startsWith('diff --git') || line.startsWith('--- ') || line.startsWith('Index: ')) {
      // If we see --- after diff --git, it's the same file
      if (line.startsWith('--- ') && currentFile && (line.includes(currentFile.from) || line.includes(currentFile.to))) {
        continue;
      }
      
      // New file started
      currentFile = {
        name: detectFileName(line, lines[i+1]),
        from: '',
        to: '',
        hunks: [],
        lines: [] // Metadata lines like 'similarity index 100%'
      };
      files.push(currentFile);
      currentHunk = null;
      
      // Try to find --- and +++ lines to get better file names
      for (let j = i; j < Math.min(i + 10, lines.length); j++) {
        if (lines[j].startsWith('--- ')) currentFile.from = lines[j].substring(4).replace(/^a\//, '');
        if (lines[j].startsWith('+++ ')) {
           currentFile.to = lines[j].substring(4).replace(/^b\//, '');
           currentFile.name = currentFile.to || currentFile.from || currentFile.name;
        }
      }
      continue;
    }
    
    // Hunk header: @@ -1,4 +1,5 @@
    const hunkMatch = line.match(/^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@/);
    if (hunkMatch) {
      const oldStart = parseInt(hunkMatch[1]);
      const newStart = parseInt(hunkMatch[3]);
      currentHunk = {
        header: line,
        oldStart: oldStart,
        oldLines: parseInt(hunkMatch[2] || '1'),
        newStart: newStart,
        newLines: parseInt(hunkMatch[4] || '1'),
        currentOld: oldStart,
        currentNew: newStart,
        lines: []
      };
      if (currentFile) {
        currentFile.hunks.push(currentHunk);
      } else {
        // Fallback for diffs without clear file headers
        currentFile = { name: 'Untitled', hunks: [currentHunk], lines: [] };
        files.push(currentFile);
      }
      continue;
    }
    
    if (currentHunk) {
      // Line within a hunk
      let type = 'context';
      let oldLine = null;
      let newLine = null;
      
      if (line.startsWith('+')) {
        type = 'add';
        newLine = currentHunk.currentNew++;
      } else if (line.startsWith('-')) {
        type = 'delete';
        oldLine = currentHunk.currentOld++;
      } else if (line.startsWith('\\')) {
          // No newline at end of file message
          type = 'meta';
      } else {
        type = 'context';
        oldLine = currentHunk.currentOld++;
        newLine = currentHunk.currentNew++;
      }
      
      currentHunk.lines.push({
        content: line,
        type: type,
        oldLine: oldLine,
        newLine: newLine
      });
    } else if (currentFile) {
      // Metadata line between file header and first hunk
      currentFile.lines.push(line);
    }
  }
  
  return files;
}

function detectFileName(line, nextLine) {
  if (line.startsWith('diff --git')) {
    const parts = line.split(' ');
    // usually "diff --git a/path/to/file b/path/to/file"
    if (parts.length >= 4) {
      return parts[3].replace(/^b\//, '');
    }
  }
  if (line.startsWith('Index: ')) {
    return line.substring(7);
  }
  if (line.startsWith('--- ')) {
    return line.substring(4).replace(/^a\//, '');
  }
  return 'Unknown';
}
