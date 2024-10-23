import requests
from PIL import Image
from io import BytesIO
from bs4 import BeautifulSoup
from transformers import AutoProcessor, BlipForConditionalGeneration
import streamlit as st
import base64
import os

# Load the pretrained processor and model
processor = AutoProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

# Function to generate a caption for an image
def caption_image(input_image: Image.Image):
    # Convert PIL image to RGB
    raw_image = input_image.convert('RGB')

    # Process the image
    inputs = processor(raw_image, return_tensors="pt")

    # Generate a caption for the image
    out = model.generate(**inputs, max_length=50)

    # Decode the generated tokens to text
    caption = processor.decode(out[0], skip_special_tokens=True)

    return caption

# Function to scrape and caption images from a URL
def scrape_and_caption_images(url):
    # Download the page
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all img elements
    img_elements = soup.find_all('img')
    captions = []

    for img_element in img_elements:
        img_url = img_element.get('src')

        # Skip if the image is an SVG or too small (likely an icon)
        if 'svg' in img_url or '1x1' in img_url:
            continue

        # Correct the URL if it's malformed
        if img_url.startswith('//'):
            img_url = 'https:' + img_url
        elif not img_url.startswith('http://') and not img_url.startswith('https://'):
            continue  # Skip URLs that don't start with http:// or https://

        try:
            # Download the image
            response = requests.get(img_url)
            raw_image = Image.open(BytesIO(response.content))

            if raw_image.size[0] * raw_image.size[1] < 400:  # Skip very small images
                continue

            raw_image = raw_image.convert('RGB')

            # Generate a caption for the image
            caption = caption_image(raw_image)

            # Store the caption along with the image URL
            captions.append((img_url, caption))
        except Exception as e:
            print(f"Error processing image {img_url}: {e}")
            continue

    return captions

# Function to save captions to a .txt file with improved structure
def save_captions_to_file(captions):
    file_content = "Image URL and Captions:\n\n"
    for index, (img_url, caption) in enumerate(captions, 1):
        file_content += f"Image {index}:\n"
        file_content += f"URL: {img_url}\n"
        file_content += f"Caption: {caption}\n"
        file_content += "-"*40 + "\n"  # Separator for readability

    # Save to a txt file in memory (BytesIO)
    txt_file = BytesIO()
    txt_file.write(file_content.encode())
    txt_file.seek(0)  # Move the cursor to the beginning

    return txt_file

# Function to set background for Streamlit app
def set_background(image_file):
    with open(image_file, "rb") as img_file:
        encoded_string = base64.b64encode(img_file.read()).decode()

    st.markdown(
        f"""
        <style>
        body {{
            background-image: url("data:image/png;base64,{encoded_string}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            height: 100vh;
            margin: 0;
            font-family: 'Times New Roman', Times, serif;
        }}
        .stApp {{
            background: transparent;
            height: 100vh;
            margin-left: -1000px;
        }}
        .main {{
            width: 100%;
        }}
        h1, h2, h3, h4, h5, h6, p, label {{
            color: white;
        }}
        .stTextInput > div > input {{
            background-color: #222;
            color: white;
        }}
        .stButton > button {{
            background-color: #800020;  /* Burgundy color */
            color: white;  /* Text color */
        }}
        .stDownloadButton > button {{
            background-color: #800020;  /* Burgundy color */
            color: white;  /* Text color for download button */
        }}
        .parsed-content {{
            color: white;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# Set background image for the app
set_background("bg.jpg")  # Replace 'bg.jpg' with the path to your background image

# Streamlit UI components
st.title("Image Captioning ")
st.write("Upload an image or scrape images from a webpage, and the model will generate captions for them.")

# Option 1: File uploader for user-uploaded image
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

# Option 2: Web scraping for images and captions
url_input = st.text_input("Or enter a URL to scrape images from", "")

# Handling uploaded file
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", use_column_width=True)

    # Generate caption for the uploaded image
    if st.button("Generate Caption for Uploaded Image"):
        with st.spinner('Generating caption...'):
            caption = caption_image(image)
            st.write("Generated Caption: ", caption)

# Handling scraping from URL
if url_input:
    if st.button("Scrape and Generate Captions"):
        with st.spinner(f'Scraping images and generating captions from {url_input}...'):
            captions = scrape_and_caption_images(url_input)

            if captions:
                # Save captions to a file and create a download button
                txt_file = save_captions_to_file(captions)
                st.download_button(
                    label="Download Captions as .txt",
                    data=txt_file,
                    file_name="captions.txt",
                    mime="text/plain",
                    key='download-button'
                )
            else:
                st.write("No valid images found or captions could not be generated.")
