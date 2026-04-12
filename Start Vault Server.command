#!/bin/bash
cd "/Users/chrisgray/Library/CloudStorage/Dropbox/1 - 2026 Documents/TV Vault New Index and Json folders"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Gray Video Vault — Local Server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Open your browser and go to:"
echo "  http://localhost:8000"
echo ""
echo "  Press Ctrl+C to stop the server."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
open "http://localhost:8000"
python3 -m http.server 8000
