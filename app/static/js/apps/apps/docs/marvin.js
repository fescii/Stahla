export default class MarvinDocs extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.renderCount = 0; // Add counter to track renders for debugging

    // Component state
    this.state = {
      activeSection: 'introduction',
      expandedSections: new Set(), // Track expanded/collapsed sections
      expandedSchemas: new Set(),  // Track expanded/collapsed schemas
      expandedSubmenu: false,      // Track submenu state for mobile
      expandedCategories: new Set(['configuration']) // Track expanded categories
    };

    this.render();
  }

  connectedCallback() {
    this._setupEventListeners();
  }

  disconnectedCallback() {
    // Clean up event listeners when element is removed
  }

  render() {
    this.renderCount++; // Increment render count for debugging
    console.log(`Rendering Marvin docs (${this.renderCount} times)`);
    this.shadowObj.innerHTML = this.getTemplate();
  }

  getTemplate() {
    return `
      ${this.getStyles()}
      <div class="marvin-docs">
        <div class="marvin-docs-content">
          <nav class="marvin-docs-sidebar">
            ${this.getSidebar()}
          </nav>
          <main id="marvin-docs-main" class="marvin-docs-main">
            <div id="content-container" class="marvin-content-container">
              ${this.getContentForSection(this.state.activeSection)}
            </div>
          </main>
        </div>
      </div>
    `;
  }

  getHeader() {
    return /* html */ `
      <header class="marvin-docs-header">
        <h1>Marvin AI Integration</h1>
        <p>A comprehensive guide to the Marvin AI integration for lead classification in the Stahla AI SDR application</p>
      </header>
    `;
  }

  getSidebar() {
    return /* html */ `
      <div class="sidebar-content">
        <div class="mobile-toggle">
          <button id="toggle-nav">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="3" y1="12" x2="21" y2="12"></line>
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="nav-sections ${this.state.expandedSubmenu ? 'expanded' : ''}">
          <div class="nav-section ${this.state.activeSection === 'introduction' ? 'active' : ''}">
            <a class="nav-link" data-section="introduction">Introduction</a>
          </div>
          <div class="nav-section ${this.state.activeSection === 'configuration' ? 'active' : ''}">
            <a class="nav-link" data-section="configuration">Configuration</a>
          </div>
          <div class="nav-section ${this.state.activeSection === 'classification' ? 'active' : ''}">
            <a class="nav-link" data-section="classification">Core Classification</a>
          </div>
          <div class="nav-section ${this.state.activeSection === 'manager' ? 'active' : ''}">
            <a class="nav-link" data-section="manager">Classification Manager</a>
          </div>
          <div class="nav-section ${this.state.activeSection === 'integration' ? 'active' : ''}">
            <a class="nav-link" data-section="integration">Integration & Workflow</a>
          </div>
          <div class="nav-section ${this.state.activeSection === 'summary' ? 'active' : ''}">
            <a class="nav-link" data-section="summary">Summary</a>
          </div>
        </div>
      </div>
    `;
  }

  getContentForSection(section) {
    switch (section) {
      case 'introduction':
        return this.getIntroductionSection();
      case 'configuration':
        return this.getConfigurationSection();
      case 'classification':
        return this.getClassificationSection();
      case 'manager':
        return this.getManagerSection();
      case 'integration':
        return this.getIntegrationSection();
      case 'summary':
        return this.getSummarySection();
      default:
        return this.getIntroductionSection();
    }
  }

  getIntroductionSection() {
    return /* html */ `
      <section id="introduction" class="content-section ${this.state.activeSection === 'introduction' ? 'active' : ''}">
        ${this.getHeader()}
        <p>This documentation details how the Marvin AI library is utilized within the Stahla AI SDR application, specifically for lead classification based on call summaries or transcripts. The integration is primarily managed through <code>app/services/classify/marvin.py</code> and used by <code>app/services/classify/classification.py</code>.</p>
        
        <p>Marvin AI provides sophisticated natural language processing capabilities that enable the Stahla AI SDR application to automatically analyze call data, extract relevant information, and classify leads based on predefined rules and patterns. This automation significantly enhances the efficiency of the lead qualification process.</p>
        
        <div class="info-block">
          <div class="info-header">Key Features</div>
          <ul>
            <li>Automatic classification of leads into predefined categories</li>
            <li>Extraction of structured information from unstructured call data</li>
            <li>Flexible integration with multiple LLM providers (OpenAI, Anthropic, Gemini)</li>
            <li>Detailed reasoning for classification decisions</li>
            <li>Fallback to rule-based classification when AI is unavailable</li>
          </ul>
        </div>
      </section>
    `;
  }

  getConfigurationSection() {
    return /* html */ `
      <section id="configuration" class="content-section ${this.state.activeSection === 'configuration' ? 'active' : ''}">
        <h2>1. Configuration</h2>
        <p>Marvin's setup is handled by the <code>configure_marvin()</code> function in <code>app/services/classify/marvin.py</code>.</p>
        
        <h3>Provider Selection</h3>
        <p>The choice of LLM provider is determined by the <code>LLM_PROVIDER</code> setting in <code>app.core.config.settings</code>. Supported providers that are explicitly configured include:</p>
        <ul>
          <li>"openai" - OpenAI's models (e.g., GPT-4)</li>
          <li>"anthropic" - Anthropic's models (e.g., Claude)</li>
          <li>"gemini" - Google's Gemini models</li>
          <li>"marvin" - Marvin's own hosted models</li>
        </ul>
        
        <h3>API Keys & Model Configuration</h3>
        <div class="code-block">
          <pre><code>def configure_marvin():
    """Configure Marvin based on application settings."""
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "openai" and settings.OPENAI_API_KEY:
        marvin.settings.openai_api_key = settings.OPENAI_API_KEY
        if settings.MODEL_NAME:
            marvin.settings.openai_model_name = settings.MODEL_NAME
            
    elif provider == "anthropic" and settings.ANTHROPIC_API_KEY:
        marvin.settings.anthropic_api_key = settings.ANTHROPIC_API_KEY
        if settings.MODEL_NAME:
            marvin.settings.anthropic_model_name = settings.MODEL_NAME
            
    elif provider == "gemini" and settings.GEMINI_API_KEY:
        marvin.settings.gemini_api_key = settings.GEMINI_API_KEY
        if settings.MODEL_NAME:
            marvin.settings.gemini_model_name = settings.MODEL_NAME
            
    # If provider is "marvin", MARVIN_API_KEY will be picked up automatically</code></pre>
          <button class="copy-btn" data-text='def configure_marvin():
    """Configure Marvin based on application settings."""
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "openai" and settings.OPENAI_API_KEY:
        marvin.settings.openai_api_key = settings.OPENAI_API_KEY
        if settings.MODEL_NAME:
            marvin.settings.openai_model_name = settings.MODEL_NAME
            
    elif provider == "anthropic" and settings.ANTHROPIC_API_KEY:
        marvin.settings.anthropic_api_key = settings.ANTHROPIC_API_KEY
        if settings.MODEL_NAME:
            marvin.settings.anthropic_model_name = settings.MODEL_NAME
            
    elif provider == "gemini" and settings.GEMINI_API_KEY:
        marvin.settings.gemini_api_key = settings.GEMINI_API_KEY
        if settings.MODEL_NAME:
            marvin.settings.gemini_model_name = settings.MODEL_NAME
            
    # If provider is "marvin", MARVIN_API_KEY will be picked up automatically'>Copy</button>
        </div>
        
        <p>The configuration function dynamically sets up Marvin based on the selected provider:</p>
        <ul>
          <li>Based on the <code>LLM_PROVIDER</code>, the function expects corresponding API key(s) (e.g., <code>OPENAI_API_KEY</code>, <code>ANTHROPIC_API_KEY</code>, <code>GEMINI_API_KEY</code>) from the application settings.</li>
          <li>An optional model name can be specified via <code>MODEL_NAME</code> in the settings.</li>
          <li>If <code>LLM_PROVIDER</code> is set to "marvin", the system assumes that <code>MARVIN_API_KEY</code> (if set in the environment or application settings) will be automatically picked up by the Marvin library.</li>
        </ul>
        
        <p>This configuration step is typically performed when the application starts or when the Marvin-related services are first initialized, ensuring Marvin is ready before being called for classification tasks.</p>
      </section>
    `;
  }

  getClassificationSection() {
    return /* html */ `
      <section id="classification" class="content-section ${this.state.activeSection === 'classification' ? 'active' : ''}">
        <h2>2. Core AI Classification Function</h2>
        
        <h3>classify_lead_with_ai</h3>
        <p>Defined in <code>app/services/classify/marvin.py</code>, this is the central Marvin-powered function for analyzing call data.</p>
        
        <div class="code-block">
          <pre><code>@marvin.fn
def classify_lead_with_ai(call_summary_or_transcript: str) -> ExtractedCallDetails:
    """
    Analyze the call summary or transcript and:
    1. Classify the lead into one of the following types: Services, Logistics, Leads, or Disqualify
    2. Extract key details about the request
    
    Classification Rules:
    - Services: Local events, short duration, and small stall requirements
    - Logistics: Non-local events or large stall requirements
    - Leads: Incomplete information or unclear requirements
    - Disqualify: Non-relevant inquiries or explicit disqualifiers
    
    [Detailed rules omitted for brevity]
    
    Extract the following information (when available):
    - Product interest (specific trailer types)
    - Service needed
    - Event type
    - Location details (full address, city, state, postal code)
    - Dates (start, end) in YYYY-MM-DD format
    - Duration in days
    - Guest count
    - Required stalls
    - Facility requirements (ADA, power, water)
    - Budget information
    - Any other relevant comments
    """</code></pre>
          <button class="copy-btn" data-text='@marvin.fn
def classify_lead_with_ai(call_summary_or_transcript: str) -> ExtractedCallDetails:
    """
    Analyze the call summary or transcript and:
    1. Classify the lead into one of the following types: Services, Logistics, Leads, or Disqualify
    2. Extract key details about the request
    
    Classification Rules:
    - Services: Local events, short duration, and small stall requirements
    - Logistics: Non-local events or large stall requirements
    - Leads: Incomplete information or unclear requirements
    - Disqualify: Non-relevant inquiries or explicit disqualifiers
    
    [Detailed rules omitted for brevity]
    
    Extract the following information (when available):
    - Product interest (specific trailer types)
    - Service needed
    - Event type
    - Location details (full address, city, state, postal code)
    - Dates (start, end) in YYYY-MM-DD format
    - Duration in days
    - Guest count
    - Required stalls
    - Facility requirements (ADA, power, water)
    - Budget information
    - Any other relevant comments
    """'>Copy</button>
        </div>
        
        <h3>Input</h3>
        <ul>
          <li><code>call_summary_or_transcript: str</code>: A string containing either a summary of the call or the full call transcript.</li>
        </ul>
        
        <h3>Output</h3>
        <p>The function returns an <code>ExtractedCallDetails</code> Pydantic Model with these fields:</p>
        
        <div class="code-block">
          <pre><code>class ExtractedCallDetails(BaseModel):
    # Primary classification
    classification: LeadClassificationType  # Services, Logistics, Leads, or Disqualify
    reasoning: str  # Explanation for the classification
    
    # Extracted details
    product_interest: Optional[List[ProductType]] = None
    service_needed: Optional[str] = None
    event_type: Optional[str] = None
    
    # Location information
    location: Optional[str] = None  # Full address
    city: Optional[str] = None
    state: Optional[str] = None  # 2-letter code
    postal_code: Optional[str] = None
    
    # Timing and scale
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None  # YYYY-MM-DD
    duration_days: Optional[int] = None
    guest_count: Optional[int] = None
    required_stalls: Optional[int] = None
    
    # Facility requirements
    ada_required: Optional[bool] = None
    power_available: Optional[bool] = None
    water_available: Optional[bool] = None
    
    # Additional information
    budget_mentioned: Optional[str] = None
    comments: Optional[str] = None</code></pre>
          <button class="copy-btn" data-text='class ExtractedCallDetails(BaseModel):
    # Primary classification
    classification: LeadClassificationType  # Services, Logistics, Leads, or Disqualify
    reasoning: str  # Explanation for the classification
    
    # Extracted details
    product_interest: Optional[List[ProductType]] = None
    service_needed: Optional[str] = None
    event_type: Optional[str] = None
    
    # Location information
    location: Optional[str] = None  # Full address
    city: Optional[str] = None
    state: Optional[str] = None  # 2-letter code
    postal_code: Optional[str] = None
    
    # Timing and scale
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None  # YYYY-MM-DD
    duration_days: Optional[int] = None
    guest_count: Optional[int] = None
    required_stalls: Optional[int] = None
    
    # Facility requirements
    ada_required: Optional[bool] = None
    power_available: Optional[bool] = None
    water_available: Optional[bool] = None
    
    # Additional information
    budget_mentioned: Optional[str] = None
    comments: Optional[str] = None'>Copy</button>
        </div>
        
        <h3>Operational Logic</h3>
        <p>The power of this Marvin function lies in its detailed docstring, which provides natural language instructions to the LLM:</p>
        <ul>
          <li><strong>Classification Rules:</strong> The docstring explicitly lists various scenarios based on combinations of "Intended Use," "Product Type," "Stalls," "Duration," and "Location" (local vs. non-local, determined by a 3-hour drive time from key service hubs).</li>
          <li><strong>Extraction Guidelines:</strong> The docstring instructs Marvin to extract specific pieces of information. A crucial instruction is that all extracted date strings <strong>must be formatted as 'YYYY-MM-DD'</strong>.</li>
          <li><strong>Disqualification Criteria:</strong> Clear conditions are provided for when a lead should be marked as "Disqualify" (e.g., incorrect information, service not offered, scam/spam, explicit non-interest).</li>
        </ul>
        
        <div class="info-block">
          <h4>Example Classification Rule</h4>
          <p>Small Event / Trailer / Local:</p>
          <ul>
            <li>Intended Use = Small Event</li>
            <li>Product Type = Any "specialty trailer"</li>
            <li>Stalls < 8</li>
            <li>Duration > 5 days</li>
            <li>Location: ≤ 3 hours drive time</li>
            <li>→ Results in "Services" classification</li>
          </ul>
        </div>
      </section>
    `;
  }

  getManagerSection() {
    return /* html */ `
      <section id="manager" class="content-section ${this.state.activeSection === 'manager' ? 'active' : ''}">
        <h2>3. MarvinClassificationManager</h2>
        <p>This class in <code>app/services/classify/marvin.py</code> acts as a wrapper and utility layer around the <code>classify_lead_with_ai</code> Marvin function.</p>
        
        <div class="code-block">
          <pre><code>class MarvinClassificationManager:
    def __init__(self):
        # Initialize Marvin configuration
        configure_marvin()
        
    def get_lead_classification(self, input_data: ClassificationInput) -> ClassificationOutput:
        """
        Process input data and return classification using Marvin AI.
        
        Args:
            input_data: The input data containing call information
            
        Returns:
            Classification result with lead type, reasoning, and metadata
        """
        # Extract call text from input data
        call_text = self._extract_call_text(input_data)
        
        if call_text:
            try:
                # Call Marvin AI function to analyze call text
                marvin_result = classify_lead_with_ai(call_text)
                
                # Create classification output from Marvin result
                output = ClassificationOutput(
                    lead_type=marvin_result.classification,
                    reasoning=marvin_result.reasoning,
                    metadata={
                        "method": "ai",
                        "processing_time_ms": 350,  # Example time
                        "model_version": "classification-v3",
                        **marvin_result.model_dump(exclude_none=True)
                    }
                )
                
                # Determine assigned team based on classification
                output.assigned_owner_team = self._get_team_for_classification(
                    marvin_result.classification
                )
                
                return output
                
            except Exception as e:
                # Handle errors in Marvin processing
                logger.error(f"Error in Marvin classification: {e}")
                return self._get_default_classification("AI processing error")
        else:
            # No call text available
            return self._get_default_classification("No call text available")
            
    def _extract_call_text(self, input_data: ClassificationInput) -> Optional[str]:
        """Extract call text from input data."""
        # Implementation details omitted
        
    def _get_team_for_classification(self, classification: str) -> str:
        """Determine team assignment based on classification."""
        # Implementation details omitted
        
    def _get_default_classification(self, reason: str) -> ClassificationOutput:
        """Create a default classification when AI processing fails."""
        # Implementation details omitted</code></pre>
          <button class="copy-btn" data-text='class MarvinClassificationManager:
    def __init__(self):
        # Initialize Marvin configuration
        configure_marvin()
        
    def get_lead_classification(self, input_data: ClassificationInput) -> ClassificationOutput:
        """
        Process input data and return classification using Marvin AI.
        
        Args:
            input_data: The input data containing call information
            
        Returns:
            Classification result with lead type, reasoning, and metadata
        """
        # Extract call text from input data
        call_text = self._extract_call_text(input_data)
        
        if call_text:
            try:
                # Call Marvin AI function to analyze call text
                marvin_result = classify_lead_with_ai(call_text)
                
                # Create classification output from Marvin result
                output = ClassificationOutput(
                    lead_type=marvin_result.classification,
                    reasoning=marvin_result.reasoning,
                    metadata={
                        "method": "ai",
                        "processing_time_ms": 350,  # Example time
                        "model_version": "classification-v3",
                        **marvin_result.model_dump(exclude_none=True)
                    }
                )
                
                # Determine assigned team based on classification
                output.assigned_owner_team = self._get_team_for_classification(
                    marvin_result.classification
                )
                
                return output
                
            except Exception as e:
                # Handle errors in Marvin processing
                logger.error(f"Error in Marvin classification: {e}")
                return self._get_default_classification("AI processing error")
        else:
            # No call text available
            return self._get_default_classification("No call text available")
            
    def _extract_call_text(self, input_data: ClassificationInput) -> Optional[str]:
        """Extract call text from input data."""
        # Implementation details omitted
        
    def _get_team_for_classification(self, classification: str) -> str:
        """Determine team assignment based on classification."""
        # Implementation details omitted
        
    def _get_default_classification(self, reason: str) -> ClassificationOutput:
        """Create a default classification when AI processing fails."""
        # Implementation details omitted'>Copy</button>
        </div>
        
        <h3>Key Method: get_lead_classification</h3>
        <p>This is the main method invoked by the higher-level <code>ClassificationManager</code>:</p>
        <ol>
          <li>It first attempts to find the call text (summary or transcript) from the <code>input_data</code> (looking in <code>extracted_data</code> and <code>raw_data</code>).</li>
          <li>If call text is found, it calls <code>classify_lead_with_ai(call_text)</code>.</li>
          <li>The <code>ExtractedCallDetails</code> object returned by Marvin is then used to construct a <code>ClassificationOutput</code> object.
            <ul>
              <li>The <code>lead_type</code> and <code>reasoning</code> are taken directly from Marvin's output.</li>
              <li>The entire <code>ExtractedCallDetails</code> object (containing all extracted fields) is converted to a dictionary using <code>model_dump(exclude_none=True)</code> and stored in the <code>metadata</code> field of the <code>ClassificationOutput</code>.</li>
            </ul>
          </li>
          <li>It also determines an <code>assigned_owner_team</code> based on the classification provided by Marvin.</li>
          <li>If no call text is available in the input, it defaults to classifying the lead as "Leads" with an appropriate error message as reasoning and sets <code>requires_human_review</code> to true.</li>
        </ol>
      </section>
    `;
  }

  getIntegrationSection() {
    return /* html */ `
      <section id="integration" class="content-section ${this.state.activeSection === 'integration' ? 'active' : ''}">
        <h2>4. Integration into the Main Classification Workflow</h2>
        <p>The <code>ClassificationManager</code> in <code>app/services/classify/classification.py</code> integrates Marvin as follows:</p>
        
        <h3>classify_lead_data Method</h3>
        <div class="code-block">
          <pre><code>def classify_lead_data(self, input_data: ClassificationInput) -> ClassificationResult:
    """
    Classify lead data using either AI or rule-based approach.
    
    Args:
        input_data: The input data to classify
        
    Returns:
        Classification result with detailed information
    """
    result = ClassificationResult()
    
    # Check if Marvin AI is enabled
    if settings.LLM_PROVIDER and settings.MARVIN_API_KEY:
        try:
            # Use Marvin for classification
            classification = self.marvin_classification_manager.get_lead_classification(input_data)
            
            # Set classification details from Marvin result
            result.lead_type = classification.lead_type
            result.reasoning = classification.reasoning
            result.assigned_owner_team = classification.assigned_owner_team
            result.metadata = classification.metadata
            
            # Determine additional fields based on classification
            result.assigned_pipeline = self._get_pipeline_for_lead_type(result.lead_type)
            result.confidence = self._calculate_confidence(result.metadata)
            result.requires_human_review = True  # Often set to true after AI processing
            result.estimated_value = self._calculate_estimated_value(result.metadata)
            
            # Normalize date fields in metadata to YYYY-MM-DD format
            self._normalize_date_fields(result.metadata)
            
            return result
            
        except Exception as e:
            logger.error(f"Error using Marvin for classification: {e}")
            # Fall back to rule-based classification
    
    # If Marvin is not enabled or failed, use rule-based classification
    rule_based_result = self.rule_based_classifier.classify(input_data)
    # Transfer rule-based result to final result
    # ... implementation details omitted
    
    return result</code></pre>
          <button class="copy-btn" data-text='def classify_lead_data(self, input_data: ClassificationInput) -> ClassificationResult:
    """
    Classify lead data using either AI or rule-based approach.
    
    Args:
        input_data: The input data to classify
        
    Returns:
        Classification result with detailed information
    """
    result = ClassificationResult()
    
    # Check if Marvin AI is enabled
    if settings.LLM_PROVIDER and settings.MARVIN_API_KEY:
        try:
            # Use Marvin for classification
            classification = self.marvin_classification_manager.get_lead_classification(input_data)
            
            # Set classification details from Marvin result
            result.lead_type = classification.lead_type
            result.reasoning = classification.reasoning
            result.assigned_owner_team = classification.assigned_owner_team
            result.metadata = classification.metadata
            
            # Determine additional fields based on classification
            result.assigned_pipeline = self._get_pipeline_for_lead_type(result.lead_type)
            result.confidence = self._calculate_confidence(result.metadata)
            result.requires_human_review = True  # Often set to true after AI processing
            result.estimated_value = self._calculate_estimated_value(result.metadata)
            
            # Normalize date fields in metadata to YYYY-MM-DD format
            self._normalize_date_fields(result.metadata)
            
            return result
            
        except Exception as e:
            logger.error(f"Error using Marvin for classification: {e}")
            # Fall back to rule-based classification
    
    # If Marvin is not enabled or failed, use rule-based classification
    rule_based_result = self.rule_based_classifier.classify(input_data)
    # Transfer rule-based result to final result
    # ... implementation details omitted
    
    return result'>Copy</button>
        </div>
        
        <h3>Integration Process</h3>
        <ol>
          <li><strong>Conditional Invocation:</strong> It checks if Marvin-based classification is enabled by verifying <code>settings.LLM_PROVIDER</code> and the presence of <code>settings.MARVIN_API_KEY</code>.</li>
          <li><strong>Marvin Execution:</strong> If enabled, it calls <code>marvin_classification_manager.get_lead_classification(input_data)</code>.</li>
          <li><strong>Result Integration:</strong> The <code>ClassificationOutput</code> from Marvin (containing <code>lead_type</code>, <code>reasoning</code>, and the rich <code>metadata</code> with all extracted fields) is used as the basis for the final classification.</li>
          <li><strong>Post-Processing & Enrichment:</strong>
            <ul>
              <li>An <code>assigned_pipeline</code> is determined based on Marvin's classification.</li>
              <li>A <code>confidence</code> score is calculated (this appears to be a separate heuristic, not directly from Marvin).</li>
              <li><code>requires_human_review</code> is set (often true after AI processing, for potential oversight).</li>
              <li>An internal <code>estimated_value</code> for the deal is calculated.</li>
              <li><strong>Date Normalization:</strong> Any date fields found within the <code>metadata</code> (which originated from Marvin's extraction) are explicitly normalized to the 'YYYY-MM-DD' string format using a utility function. This acts as a safeguard or correction step, even though Marvin was instructed to provide dates in this format.</li>
            </ul>
          </li>
          <li><strong>Fallback:</strong> If Marvin is not enabled, the system falls back to a purely rule-based classification defined in <code>app/services/classify/rules.py</code>.</li>
        </ol>
      </section>
    `;
  }

  getSummarySection() {
    return /* html */ `
      <section id="summary" class="content-section ${this.state.activeSection === 'summary' ? 'active' : ''}">
        <h2>Summary of Marvin's Role</h2>
        <p>If enabled, Marvin AI, through the <code>@marvin.fn classify_lead_with_ai</code> function, takes on the primary responsibility of:</p>
        
        <ol>
          <li><strong>Classifying the lead</strong> into predefined categories based on complex rules provided in natural language.</li>
          <li><strong>Extracting a wide array of structured details</strong> from the unstructured call text.</li>
          <li>Providing <strong>reasoning</strong> for its classification.</li>
        </ol>
        
        <p>The application then takes this rich, structured output from Marvin, stores the extracted details in the <code>metadata</code> field of its classification result, and performs minor additional processing (like date normalization and confidence scoring) before finalizing the <code>ClassificationResult</code>.</p>
        
        <p>This architecture allows the system to leverage Large Language Models for nuanced understanding of call data while maintaining a structured approach to lead processing.</p>
        
        <h3>Key Benefits</h3>
        <div class="info-block">
          <ul>
            <li><strong>Natural Language Understanding:</strong> Ability to extract meaning from unstructured text</li>
            <li><strong>Flexible Classification Rules:</strong> Rules expressed in natural language instead of rigid code</li>
            <li><strong>Rich Information Extraction:</strong> Automatically identifies and extracts dozens of fields from conversations</li>
            <li><strong>Graceful Degradation:</strong> Falls back to rule-based classification when AI is unavailable</li>
            <li><strong>Transparent Reasoning:</strong> Provides explanations for classification decisions</li>
          </ul>
        </div>
      </section>
    `;
  }

  _setupEventListeners() {
    // Handle navigation link clicks
    this.shadowObj.addEventListener('click', (event) => {
      const navLink = event.target.closest('.nav-link');
      if (navLink) {
        const section = navLink.dataset.section;
        const category = navLink.dataset.category;
        
        if (category) {
          this._toggleCategoryExpansion(category);
        } else if (section) {
          this._navigateToSection(section);
        }
      }
      
      // Toggle mobile nav
      if (event.target.closest('#toggle-nav')) {
        this.state.expandedSubmenu = !this.state.expandedSubmenu;
        this.render();
      }
      
      // Handle copy button clicks
      const copyBtn = event.target.closest('.copy-btn');
      if (copyBtn) {
        const textToCopy = copyBtn.dataset.text;
        if (textToCopy) {
          navigator.clipboard.writeText(textToCopy).then(() => {
            const originalText = copyBtn.innerText;
            copyBtn.innerText = 'Copied!';
            setTimeout(() => {
              copyBtn.innerText = originalText;
            }, 2000);
          });
        }
      }
    });
  }
  
  /**
   * Toggle category expansion in the sidebar
   * @param {string} category - The category to toggle
   */
  _toggleCategoryExpansion(category) {
    if (this.state.expandedCategories.has(category)) {
      this.state.expandedCategories.delete(category);
    } else {
      this.state.expandedCategories.add(category);
    }
    this.render();
  }
  
  /**
   * Navigate to a specific section
   * @param {string} section - The section to navigate to
   */
  _navigateToSection(section) {
    this.state.activeSection = section;
    this.render();
    
    // Ensure the linked section is visible
    const sectionElement = this.shadowObj.getElementById(section);
    // if (sectionElement) {
    //   sectionElement.scrollIntoView({ behavior: 'smooth' });
    // }
  }

  _toggleSectionExpansion(sectionId, sectionElement, buttonElement) {
    if (this.state.expandedSections.has(sectionId)) {
      this.state.expandedSections.delete(sectionId);
      sectionElement.classList.remove('expanded');
      buttonElement.querySelector('.icon').textContent = '+';
    } else {
      this.state.expandedSections.add(sectionId);
      sectionElement.classList.add('expanded');
      buttonElement.querySelector('.icon').textContent = '−';
    }
  }

  getStyles() {
    return /* CSS */`
      <style>
        :host {
          display: block;
          width: 100%;
          font-family: var(--font-main);
          color: var(--text-color);
          line-height: 1.6;
        }
        
        *,
        *:after,
        *:before {
          box-sizing: border-box;
          font-family: inherit;
          -webkit-box-sizing: border-box;
        }

        *:focus {
          outline: inherit !important;
        }

        *::-webkit-scrollbar {
          width: 3px;
        }

        *::-webkit-scrollbar-track {
          background: var(--scroll-bar-background);
        }

        *::-webkit-scrollbar-thumb {
          width: 3px;
          background: var(--scroll-bar-linear);
          border-radius: 50px;
        }
        
        .marvin-docs {
          width: 100%;
          padding: 0 10px;
          margin: 0;
          display: flex;
          flex-flow: column;
          gap: 20px;
        }
        
        .marvin-docs-header {
          padding: 0;
        }
        
        .marvin-docs-header h1 {
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0;
          padding: 0;
          line-height: 1.4;
          color: var(--title-color);
        }
        
        .marvin-docs-header p {
          font-size: 1rem;
          margin: 0;
          padding: 0;
          color: var(--gray-color);
        }
        
        .marvin-docs-content {
          display: flex;
          width: 100%;
          flex-flow: row-reverse;
          justify-content: space-between;
          gap: 20px;
        }
        
        .marvin-docs-sidebar {
          width: 260px;
          position: sticky;
          top: 20px;
          height: calc(100vh - 40px);
          padding-right: 10px;
          overflow-y: auto;
          position: sticky;
          overflow: auto;
          -ms-overflow-style: none; /* IE 11 */
          scrollbar-width: none; /* Firefox 64 */
        }

        .marvin-docs-sidebar::-webkit-scrollbar {
          display: none;
        }
        
        .sidebar-content {
          border-radius: 8px;
          background-color: var(--background);
        }
        
        .nav-sections {
          padding: 0;
        }
        
        .nav-section {
          padding: 0;
          margin-bottom: 5px;
        }
        
        .nav-link {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 8px 15px;
          font-size: 0.9rem;
          color: var(--text-color);
          text-decoration: none;
          border-radius: 6px;
          cursor: pointer;
          transition: background-color 0.2s;
        }
        
        .nav-section.active .nav-link:hover {
          background-color: var(--tab-background);
        }
        
        .nav-link:hover {
          background-color: var(--hover-background);
        }
        
        .nav-section.active > .nav-link {
          background-color: var(--tab-background);
          color: var(--accent-color);
          font-weight: 500;
        }
        
        .nav-link.parent {
          font-weight: 600;
          color: var(--text-color);
        }
        
        .nav-link.sub {
          padding-left: 32px;
          font-size: 0.9rem;
          position: relative;
          display: flex;
        }

        div.subnav > a.nav-link.sub::before {
          content: '-';
          position: absolute;
          left: 16px;
          top: 50%;
          transform: translateY(-50%);
          z-index: 1;
        }
        
        .subnav {
          max-height: 0;
          overflow: hidden;
          transition: max-height 0.3s ease-out;
        }
        
        .nav-section.expanded .subnav {
          max-height: 500px;
          transition: max-height 0.5s ease-in;
        }
        
        .nav-section.collapsed .subnav {
          max-height: 0;
        }
        
        .mobile-toggle {
          display: none;
        }
        
        .marvin-docs-main {
          flex: 1;
          padding: 20px 0;
          min-width: 0;
        }
        
        .marvin-content-container {
          padding: 0;
        }
        
        .content-section {
          display: none;
          padding: 0;
          background-color: var(--background);
          border-radius: 8px;
        }
        
        .content-section.active {
          display: block;
        }
        
        .content-section h2 {
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0 0 20px;
          color: var(--title-color);
        }
        
        .content-section h3 {
          font-size: 1.4rem;
          font-weight: 500;
          margin: 30px 0 15px;
          color: var(--title-color);
        }

        .content-section .info-header {
          font-size: 1.2rem;
          font-weight: 500;
          margin: 0 0 10px;
          color: var(--title-color);
        }
        
        .content-section h4 {
          font-size: 1.1rem;
          font-weight: 500;
          margin: 25px 0 10px;
          color: var(--title-color);
        }
        
        .content-section p {
          margin: 0 0 15px;
        }
        
        .content-section ul, .content-section ol {
          margin: 0 0 15px;
          padding-left: 25px;
        }
        
        .content-section li {
          margin-bottom: 8px;
        }
        
        .content-section code {
          font-family: var(--font-mono);
          background-color: var(--stat-background);
          padding: 2px 5px;
          border-radius: 4px;
          font-size: 0.9em;
        }
        
        .code-block {
          position: relative;
          margin: 15px 0;
          border-radius: 8px;
          overflow: hidden;
        }
        
        .code-block pre {
          margin: 0;
          padding: 15px;
          background-color: var(--stat-background);
          border-radius: 8px;
          overflow-x: auto;
          font-family: var(--font-mono);
          font-size: 0.85rem;
        }
        
        .code-block code {
          background: none;
          padding: 0;
          border-radius: 0;
          font-family: var(--font-mono);
        }
        
        .copy-btn {
          position: absolute;
          top: 5px;
          right: 5px;
          padding: 3px 8px;
          background-color: var(--background);
          border: var(--border-button);
          color: var(--text-color);
          border-radius: 4px;
          font-size: 0.75rem;
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .copy-btn:hover {
          background-color: var(--hover-background);
        }
        
        .info-block {
          background-color: var(--stat-background);
          padding: 15px 12px;
          margin: 15px 0;
          border-radius: 6px;
        }
        
        @media (max-width: 900px) {
          .marvin-docs-content {
            flex-direction: column;
          }
          
          .marvin-docs-sidebar {
            width: 100%;
            position: relative;
            top: 0;
            height: auto;
            max-height: 300px;
            overflow-y: hidden;
          }
          
          .mobile-toggle {
            display: block;
            padding: 10px 15px;
            border-bottom: var(--border);
          }
          
          .mobile-toggle button {
            background: none;
            border: none;
            color: var(--text-color);
            cursor: pointer;
            padding: 5px;
            display: flex;
            align-items: center;
            justify-content: center;
          }
          
          .nav-sections {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
            padding: 0;
          }
          
          .nav-sections.expanded {
            max-height: 500px;
            overflow-y: auto;
            transition: max-height 0.5s ease-in;
            padding: 15px 0;
          }
        }
      </style>
    `;
  }
}