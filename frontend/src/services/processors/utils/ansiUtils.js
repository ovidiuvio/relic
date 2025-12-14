/**
 * Parse ANSI escape codes and generate Monaco decorations with full SGR support
 * Returns { text: cleanedText, decorations: [...] }
 */
export function parseAnsiCodes(text) {
    // VS Code dark theme color palette (more readable than pure ANSI)
    const fgColorMap = {
        30: '#000000', 31: '#CD3131', 32: '#0DBC79', 33: '#E5E510',
        34: '#2472C8', 35: '#BC3FBC', 36: '#11A8CD', 37: '#E5E5E5',
        90: '#666666', 91: '#F14C4C', 92: '#23D18B', 93: '#F5F543',
        94: '#3B8EEA', 95: '#D670D6', 96: '#29B8DB', 97: '#FFFFFF'
    }

    const bgColorMap = {
        40: '#000000', 41: '#CD3131', 42: '#0DBC79', 43: '#E5E510',
        44: '#2472C8', 45: '#BC3FBC', 46: '#11A8CD', 47: '#E5E5E5',
        100: '#666666', 101: '#F14C4C', 102: '#23D18B', 103: '#F5F543',
        104: '#3B8EEA', 105: '#D670D6', 106: '#29B8DB', 107: '#FFFFFF'
    }

    // 256-color palette (xterm colors)
    const get256Color = (n) => {
        if (n < 16) {
            // VS Code dark theme colors (0-15)
            const stdColors = ['#000000', '#CD3131', '#0DBC79', '#E5E510', '#2472C8', '#BC3FBC', '#11A8CD', '#E5E5E5',
                '#666666', '#F14C4C', '#23D18B', '#F5F543', '#3B8EEA', '#D670D6', '#29B8DB', '#FFFFFF']
            return stdColors[n]
        } else if (n < 232) {
            // 6x6x6 RGB cube (16-231)
            const idx = n - 16
            const r = Math.floor(idx / 36)
            const g = Math.floor((idx % 36) / 6)
            const b = idx % 6
            const toHex = (v) => (v === 0 ? 0 : 55 + v * 40).toString(16).padStart(2, '0')
            return `#${toHex(r)}${toHex(g)}${toHex(b)}`
        } else {
            // Grayscale (232-255)
            const gray = 8 + (n - 232) * 10
            const hex = gray.toString(16).padStart(2, '0')
            return `#${hex}${hex}${hex}`
        }
    }

    const decorations = []
    let cleanText = ''
    let rangeStart = 0

    // Current style state
    const state = {
        fgColor: null,
        bgColor: null,
        bold: false,
        dim: false,
        italic: false,
        underline: false,
        blink: false,
        reverse: false,
        hidden: false,
        strikethrough: false
    }

    const hasActiveStyle = () => {
        return state.fgColor || state.bgColor || state.bold || state.dim ||
            state.italic || state.underline || state.blink || state.reverse ||
            state.hidden || state.strikethrough
    }

    const saveDecoration = () => {
        if (hasActiveStyle() && cleanText.length > rangeStart) {
            const options = {}
            if (state.fgColor) options.color = state.fgColor
            if (state.bgColor) options.backgroundColor = state.bgColor
            if (state.bold) options.bold = true
            if (state.dim) options.dim = true
            if (state.italic) options.italic = true
            if (state.underline) options.underline = true
            if (state.blink) options.blink = true
            if (state.reverse) options.reverse = true
            if (state.hidden) options.hidden = true
            if (state.strikethrough) options.strikethrough = true

            decorations.push({
                range: { start: rangeStart, end: cleanText.length },
                options
            })
        }
    }

    // eslint-disable-next-line no-control-regex
    const parts = text.split(/(\x1B\[[0-9;]*[a-zA-Z])/)

    for (const part of parts) {
        // eslint-disable-next-line no-control-regex
        const match = part.match(/^\x1B\[([0-9;]*)([a-zA-Z])$/)

        if (match) {
            const codes = match[1] ? match[1].split(';').map(Number) : [0]
            const command = match[2]

            if (command === 'm') {
                // Save current decoration before changing state
                saveDecoration()

                // Process SGR codes
                let i = 0
                while (i < codes.length) {
                    const code = codes[i]

                    if (code === 0) {
                        // Reset all attributes
                        Object.keys(state).forEach(key => state[key] = key.includes('Color') ? null : false)
                    } else if (code === 1) {
                        state.bold = true
                    } else if (code === 2) {
                        state.dim = true
                    } else if (code === 3) {
                        state.italic = true
                    } else if (code === 4) {
                        state.underline = true
                    } else if (code === 5 || code === 6) {
                        state.blink = true
                    } else if (code === 7) {
                        state.reverse = true
                    } else if (code === 8) {
                        state.hidden = true
                    } else if (code === 9) {
                        state.strikethrough = true
                    } else if (code === 22) {
                        state.bold = false
                        state.dim = false
                    } else if (code === 23) {
                        state.italic = false
                    } else if (code === 24) {
                        state.underline = false
                    } else if (code === 25) {
                        state.blink = false
                    } else if (code === 27) {
                        state.reverse = false
                    } else if (code === 28) {
                        state.hidden = false
                    } else if (code === 29) {
                        state.strikethrough = false
                    } else if (code >= 30 && code <= 37) {
                        state.fgColor = fgColorMap[code]
                    } else if (code === 38) {
                        // Extended foreground color
                        if (codes[i + 1] === 5 && codes[i + 2] !== undefined) {
                            // 256-color mode
                            state.fgColor = get256Color(codes[i + 2])
                            i += 2
                        } else if (codes[i + 1] === 2 && codes[i + 4] !== undefined) {
                            // RGB mode
                            const r = codes[i + 2]
                            const g = codes[i + 3]
                            const b = codes[i + 4]
                            state.fgColor = `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`
                            i += 4
                        }
                    } else if (code === 39) {
                        state.fgColor = null
                    } else if (code >= 40 && code <= 47) {
                        state.bgColor = bgColorMap[code]
                    } else if (code === 48) {
                        // Extended background color
                        if (codes[i + 1] === 5 && codes[i + 2] !== undefined) {
                            // 256-color mode
                            state.bgColor = get256Color(codes[i + 2])
                            i += 2
                        } else if (codes[i + 1] === 2 && codes[i + 4] !== undefined) {
                            // RGB mode
                            const r = codes[i + 2]
                            const g = codes[i + 3]
                            const b = codes[i + 4]
                            state.bgColor = `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`
                            i += 4
                        }
                    } else if (code === 49) {
                        state.bgColor = null
                    } else if (code >= 90 && code <= 97) {
                        state.fgColor = fgColorMap[code]
                    } else if (code >= 100 && code <= 107) {
                        state.bgColor = bgColorMap[code]
                    }

                    i++
                }

                rangeStart = cleanText.length
            }
        } else if (part) {
            cleanText += part
        }
    }

    // Save final decoration
    saveDecoration()

    return { text: cleanText, decorations }
}

/**
 * Check if text contains ANSI escape codes
 */
export function containsAnsiCodes(text) {
    // eslint-disable-next-line no-control-regex
    return /\x1B\[[0-9;]*[a-zA-Z]/.test(text)
}
