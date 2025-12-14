
import { processCode, detectLanguage, highlightCode } from './codeProcessor.js';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

export async function processNotebook(content) {
    try {
        const text = new TextDecoder("utf-8").decode(content);
        const notebook = JSON.parse(text);

        const cells = await Promise.all(notebook.cells.map(async (cell, index) => {
            const cellSource = Array.isArray(cell.source) ? cell.source.join('') : (cell.source || '');

            if (cell.cell_type === 'markdown') {
                const html = DOMPurify.sanitize(marked.parse(cellSource));
                return {
                    type: 'markdown',
                    content: html,
                    id: index
                };
            } else if (cell.cell_type === 'code') {
                const language = notebook.metadata?.kernelspec?.language || 'python';
                const highlighted = await highlightCode(cellSource, language);

                const outputs = (cell.outputs || []).map(output => {
                    if (output.output_type === 'stream') {
                        return {
                            type: 'text',
                            content: Array.isArray(output.text) ? output.text.join('') : output.text
                        };
                    } else if (output.output_type === 'execute_result' || output.output_type === 'display_data') {
                        const data = output.data || {};

                        if (data['text/html']) {
                            return {
                                type: 'html',
                                content: DOMPurify.sanitize(Array.isArray(data['text/html']) ? data['text/html'].join('') : data['text/html'])
                            };
                        } else if (data['image/png']) {
                            return {
                                type: 'image',
                                format: 'png',
                                content: Array.isArray(data['image/png']) ? data['image/png'].join('') : data['image/png']
                            };
                        } else if (data['image/jpeg']) {
                            return {
                                type: 'image',
                                format: 'jpeg',
                                content: Array.isArray(data['image/jpeg']) ? data['image/jpeg'].join('') : data['image/jpeg']
                            };
                        } else if (data['text/plain']) {
                            return {
                                type: 'text',
                                content: Array.isArray(data['text/plain']) ? data['text/plain'].join('') : data['text/plain']
                            };
                        }
                    } else if (output.output_type === 'error') {
                        return {
                            type: 'error',
                            ename: output.ename,
                            evalue: output.evalue,
                            traceback: output.traceback
                        };
                    }
                    return null;
                }).filter(Boolean);

                return {
                    type: 'code',
                    source: highlighted,
                    outputs: outputs,
                    execution_count: cell.execution_count,
                    id: index
                };
            }
            return null;
        }));

        return {
            type: 'notebook',
            metadata: notebook.metadata,
            cells: cells.filter(Boolean)
        };
    } catch (e) {
        console.error("Error processing notebook:", e);
        return {
            type: 'text',
            content: new TextDecoder("utf-8").decode(content),
            error: "Failed to parse notebook"
        };
    }
}
