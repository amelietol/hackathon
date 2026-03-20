# Streamlit Community Cloud Deployment Guide

## Quick Setup

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Prepare for Streamlit Cloud deployment"
   git push origin main
   ```

2. **Deploy on Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Select your GitHub repository
   - Set main file path: `simulation/app.py`
   - Click "Deploy"

3. **Configure Secrets**
   - In your deployed app, go to: **Settings > Secrets**
   - Copy contents from `.streamlit/secrets.toml.example`
   - Replace with your actual AWS credentials from Workshop Studio
   - Click "Save"

## AWS Credentials

Get your temporary credentials from AWS Workshop Studio:
1. Go to your Workshop Studio event page
2. Click "Get AWS CLI credentials"
3. Copy the values for:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_SESSION_TOKEN`

**Note**: Workshop Studio credentials expire. You'll need to update them in Streamlit Cloud secrets when they expire.

## Important Notes

### Simulation Loop
The app currently expects `sim.py` to run separately. For Streamlit Cloud, the simulation logic runs within the Streamlit app itself (via the auto-rerun every 1 second).

### File Paths
All image files (background, astronauts, plants) must be in the `simulation/` directory since that's where `app.py` runs from.

### Agent Bridge
The `agent_bridge.py` is optional. If you're not using the AWS Bedrock agents, the app will still work for the basic simulation.

## Troubleshooting

**Images not loading?**
- Ensure all `.png` and `.jpeg` files are in the `simulation/` directory
- Check that image filenames match exactly (case-sensitive)

**AWS errors?**
- Verify secrets are set correctly in Streamlit Cloud
- Check that credentials haven't expired
- Ensure ARNs are correct for your AWS account

**App not updating?**
- The app auto-refreshes every 1 second
- Check that `state.json` and `control.json` are being created
- Look at logs in Streamlit Cloud dashboard
