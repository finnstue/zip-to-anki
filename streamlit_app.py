import streamlit as st
import pandas as pd
import os
import genanki
import tempfile
from pathlib import Path
import zipfile

st.title("CSV to Anki APKG Converter")

st.markdown("""
This app converts a ZIP file containing a CSV file of Anki flashcards (with optional images) into an Anki `.apkg` package for import.

- **ZIP contents required:** `your_flashcards.csv` and optionally an `images` folder
- **Image support:** If your cards reference images (e.g., `<img src=...>`), include them in the `images` folder within the ZIP.
""")

zip_file = st.file_uploader("Upload a ZIP file containing your Anki CSV and images folder", type=["zip"])
output_filename = st.text_input("Output APKG filename", "diana-flashcards", help="Will be saved as <this>.apkg")

if st.button("Convert and Download"):
    if not zip_file:
        st.error("Please upload a ZIP file.")
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save ZIP to temp file
            zip_path = os.path.join(tmpdir, "input.zip")
            with open(zip_path, "wb") as f:
                f.write(zip_file.read())
            # Extract zip
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)
            # Find CSV file (first .csv in extracted dir)
            csv_path = None
            images_dir = None
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    if file.lower().endswith('.csv') and csv_path is None:
                        csv_path = os.path.join(root, file)
                for d in dirs:
                    if d.lower() == 'images':
                        images_dir = os.path.join(root, d)
            if not csv_path:
                st.error("No CSV file found in the ZIP.")
            else:
                # Set output filename to match CSV if user left default
                default_name = "diana-flashcards"
                if output_filename == default_name:
                    csv_base = os.path.splitext(os.path.basename(csv_path))[0]
                    output_filename = csv_base
                df = pd.read_csv(csv_path)

                # Fix image references: remove 'images/' from src
                def fix_img_paths(text):
                    if isinstance(text, str):
                        return text.replace('src="images/', 'src="')
                    return text

                df['Question'] = df['Question'].apply(fix_img_paths)
                df['Answer'] = df['Answer'].apply(fix_img_paths)

                # Prepare Anki deck/model
                deck_name = output_filename
                if deck_name.lower().endswith('.apkg'):
                    deck_name = deck_name[:-5]
                my_model = genanki.Model(
                    1607392319,
                    'Simple Model',
                    fields=[
                        {'name': 'Question'},
                        {'name': 'Answer'},
                    ],
                    templates=[
                        {
                            'name': 'Card 1',
                            'qfmt': '{{Question}}',
                            'afmt': '{{Question}}<hr id="answer">{{Answer}}',
                        },
                    ],
                    css="""
.card {
  font-family: arial;
  font-size: 20px;
  text-align: center;
  color: black;
  background-color: white;
}
"""
                )

                my_deck = genanki.Deck(
                    2059400110,
                    deck_name
                )

                # Add notes
                for idx, row in df.iterrows():
                    note = genanki.Note(
                        model=my_model,
                        fields=[str(row['Question']), str(row['Answer'])]
                    )
                    my_deck.add_note(note)

                # Collect all images if image_dir is provided
                media_files = []
                if images_dir:
                    for file in Path(images_dir).glob("**/*"):
                        if file.is_file():
                            media_files.append(str(file))

                # Ensure output filename ends with .apkg
                final_output_filename = output_filename
                if not final_output_filename.lower().endswith('.apkg'):
                    final_output_filename += '.apkg'

                # Write the .apkg file
                apkg_path = os.path.join(tmpdir, final_output_filename)
                genanki.Package(my_deck, media_files=media_files).write_to_file(apkg_path)

                st.success(f"APKG file created: {final_output_filename}")
                with open(apkg_path, "rb") as f:
                    st.download_button(
                        label="Download APKG",
                        data=f,
                        file_name=final_output_filename,
                        mime="application/octet-stream"
                    )
