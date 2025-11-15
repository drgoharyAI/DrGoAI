---
title: Dr GO AI - Medical Pre-Authorization
emoji: 🏥
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: "4.44.0"
app_file: app.py
pinned: false
license: mit
---

# 🏥 Dr GO AI - Medical Pre-Authorization System

Advanced AI-powered medical pre-authorization system for healthcare insurance in the Kingdom of Saudi Arabia.

## Features

✨ **Enhanced FHIR Display** - Comprehensive clinical data visualization
- Patient & Insurance Details
- Clinical Summary with ICD-10 Diagnoses
- Body Metrics (Vital Signs)
- Supporting Clinical Information
- Requested Services with Pricing
- Approvals & Claims History

🤖 **AI-Powered Analysis** - Intelligent claim review
- Medical necessity evaluation
- Policy compliance checking
- Risk assessment scoring
- Arabic language support

📊 **Complete Workflow**
- FHIR R4 bundle parsing
- OCR for document processing
- Rules engine for policy enforcement
- Comprehensive reporting

## Quick Start

### Default Login Credentials

**Admin Account:**
- Username: `admin`
- Password: `admin123`

**Reviewer Account:**
- Username: `reviewer`
- Password: `reviewer123`

### Upload FHIR Data

1. Login with credentials above
2. Go to "Workbench" tab
3. Upload your FHIR Bundle JSON file
4. Review the comprehensive parsed clinical data
5. Run AI analysis for automated decision support

## System Requirements

- Python 3.8+
- Gradio 4.x
- Standard Python libraries

## Technical Details

### Supported Standards
- **FHIR**: R4
- **Coding Systems**: ICD-10, NAPHIES
- **Currency**: SAR (Saudi Riyal)
- **Language**: English & Arabic

### Architecture
- **Frontend**: Gradio web interface
- **Parser**: Enhanced FHIR R4 parser
- **AI**: Local LLM (Ollama) or Cloud (Gemini)
- **Storage**: CSV-based (portable)

## Features in Detail

### Enhanced FHIR Display
The system provides a comprehensive, collapsible display of all FHIR data including:
- Complete patient demographics
- Insurance and coverage details
- Clinical diagnoses with ICD codes
- Vital signs and body metrics
- All supporting clinical information
- Detailed service requests with billing

### AI Analysis
- Evaluates medical necessity
- Checks policy compliance
- Calculates risk scores
- Identifies potential issues
- Generates comprehensive reports in English and Arabic

### Rules Engine
- Configurable business rules
- AI-assisted rule generation
- Priority-based evaluation
- Override capabilities

## For Healthcare Providers in KSA

This system is specifically designed for the Saudi healthcare system:
- NAPHIES compliance
- Support for local coding standards
- SAR currency handling
- Arabic language support
- Integration-ready for KSA health insurance workflows

## Configuration

### AI Provider Settings
Navigate to Settings tab to configure:
- **Local**: Ollama (recommended for privacy)
- **Cloud**: Google Gemini (requires API key)

### Rules Management
Configure automated decision rules in the Configuration tab

## Security & Privacy

- Local-first processing
- No data leaves your system (when using Ollama)
- Authentication required
- Role-based access control (Admin/Reviewer)

## Documentation

Complete documentation available in the repository:
- Integration guides
- Technical specifications
- API documentation
- Customization guides

## Support

For healthcare organizations in Saudi Arabia looking to implement this system, please refer to the comprehensive documentation included in the repository.

## License

MIT License - See LICENSE file for details

## Acknowledgments

Built for the Kingdom of Saudi Arabia healthcare system with support for NAPHIES standards and local requirements.

---

**Status**: ✅ Production Ready  
**Version**: 1.0  
**Last Updated**: November 2025  
**Region**: Kingdom of Saudi Arabia  
**Standards**: FHIR R4, NAPHIES, ICD-10
