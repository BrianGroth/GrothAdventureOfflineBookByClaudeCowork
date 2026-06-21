Font files required for the Groth Adventures Scrapbook UI.

Download these variable font files and place them in this directory:

1. PlayfairDisplay-VariableFont_wght.woff2
   Source: https://fonts.google.com/specimen/Playfair+Display
   Used for: headings, titles, display text

2. Lora-VariableFont_wght.woff2
   Source: https://fonts.google.com/specimen/Lora
   Used for: body text, article content

3. Inter-VariableFont.woff2
   Source: https://fonts.google.com/specimen/Inter
   Used for: UI elements, labels, navigation

All three fonts are open-source (SIL Open Font License).

Quick download via command line:
  curl -L "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf" -o PlayfairDisplay.ttf
  # Then convert TTF to WOFF2 using: https://cloudconvert.com/ttf-to-woff2

Or use Google Fonts CSS API (requires internet connection) by replacing the
@font-face declarations in src/styles/theme.css with:
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400..900&family=Lora:wght@400..700&family=Inter:wght@300..700&display=swap');

The app works without these fonts but falls back to Georgia / system-ui.
