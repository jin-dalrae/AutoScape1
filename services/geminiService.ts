// geminiService.ts
// This file contains the logic for interacting with the Google GenAI API
// It is used to generate landscape designs based on user input


import { GoogleGenAI } from "@google/genai";
import { AnalysisSchema, GeneratedDesign } from "../types";

// PRO model for reasoning, scene understanding, and complex JSON analysis
const MODEL_REASONING = "gemini-3-pro-preview";

// FLASH-IMAGE model for fast, high-quality visual generation
const MODEL_GENERATION = "gemini-2.5-flash-image";

// Helper to convert file to base64 string
const fileToGenericBase64 = async (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      const base64 = result.split(',')[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
};

const extractImage = (res: any): string | null => {
  for (const part of res.candidates?.[0]?.content?.parts || []) {
    if (part.inlineData) {
      return `data:${part.inlineData.mimeType};base64,${part.inlineData.data}`;
    }
  }
  return null;
};

const GEMINI_API_KEY =
  import.meta.env.VITE_GEMINI_API_KEY ||
  import.meta.env.VITE_API_KEY ||
  process.env.GEMINI_API_KEY ||
  process.env.API_KEY;

// Timeout helper for long-running operations
const withTimeout = async <T>(
  promise: Promise<T>,
  timeoutMs: number,
  operationName: string = 'Operation'
): Promise<T> => {
  let timeoutId: NodeJS.Timeout;

  const timeoutPromise = new Promise<never>((_, reject) => {
    timeoutId = setTimeout(() => {
      reject(new Error(`${operationName} timed out after ${timeoutMs / 1000} seconds. Please try again.`));
    }, timeoutMs);
  });

  try {
    const result = await Promise.race([promise, timeoutPromise]);
    clearTimeout(timeoutId!);
    return result;
  } catch (error) {
    clearTimeout(timeoutId!);
    throw error;
  }
};

// Generation timeout configuration (2 minutes per phase, 5 minutes total)
const PHASE_TIMEOUT_MS = 120000; // 2 minutes per phase
const TOTAL_TIMEOUT_MS = 300000; // 5 minutes total

// Retry helper for Gemini API calls (handles transient 500 errors)
const retryOperation = async <T>(
  operation: () => Promise<T>,
  maxRetries: number = 3,
  delayMs: number = 2000
): Promise<T> => {
  let lastError: Error | null = null;
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error: any) {
      lastError = error;
      const isRetryable =
        error?.message?.includes('500') ||
        error?.message?.includes('INTERNAL') ||
        error?.message?.includes('Internal error');

      if (isRetryable && attempt < maxRetries) {
        console.warn(`⚠️ Gemini API error (attempt ${attempt}/${maxRetries}), retrying in ${delayMs}ms...`, error?.message);
        await new Promise(resolve => setTimeout(resolve, delayMs * attempt));
      } else {
        throw error;
      }
    }
  }
  throw lastError;
};

// Validate if uploaded image is appropriate for landscape design
export interface ImageValidationResult {
  isValid: boolean;
  message: string;
  imageType?: string;
}

export const validateImageContent = async (
  file: File
): Promise<ImageValidationResult> => {
  if (!GEMINI_API_KEY) {
    // If no API key, skip validation
    return { isValid: true, message: "Validation skipped" };
  }

  try {
    const ai = new GoogleGenAI({ apiKey: GEMINI_API_KEY });
    const base64 = await fileToGenericBase64(file);

    const validationPrompt = `Analyze this image and determine if it's appropriate for landscape design.

VALID images include:
- Outdoor yards, gardens, lawns
- Patios, decks, outdoor living spaces
- Front or back yards
- Driveways, pathways
- Empty outdoor spaces
- Landscapes, outdoor areas

INVALID images include:
- Human faces or portraits
- Selfies
- Indoor rooms (living rooms, bedrooms, kitchens)
- Screenshots, documents, text
- Animals close-ups
- Food
- Completely unrelated content

Respond with ONLY a JSON object in this exact format:
{"isValid": true/false, "imageType": "brief description of what the image shows", "message": "explanation if invalid"}

If valid, message should be empty string. If invalid, message should politely explain what's wrong.`;

    const response = await ai.models.generateContent({
      model: "gemini-2.0-flash",
      contents: [
        {
          role: "user",
          parts: [
            { inlineData: { mimeType: file.type || "image/jpeg", data: base64 } },
            { text: validationPrompt }
          ]
        }
      ],
      config: {
        temperature: 0.1,
        maxOutputTokens: 200
      }
    });

    const text = response.text || "";
    const jsonMatch = text.match(/\{[\s\S]*\}/);

    if (jsonMatch) {
      const result = JSON.parse(jsonMatch[0]);
      return {
        isValid: result.isValid === true,
        message: result.message || "",
        imageType: result.imageType
      };
    }

    // Default to valid if parsing fails
    return { isValid: true, message: "" };
  } catch (error: any) {
    console.error("Image validation failed:", error);
    // Fail closed for security - reject on validation errors
    // Network errors get a more helpful message
    const isNetworkError = error?.message?.includes('network') ||
                           error?.message?.includes('fetch') ||
                           error?.message?.includes('CORS');

    if (isNetworkError) {
      return {
        isValid: false,
        message: "Unable to validate image due to network issues. Please check your connection and try again."
      };
    }

    return {
      isValid: false,
      message: "Unable to validate image. Please try uploading a different image or try again later."
    };
  }
};


// Helper to approximate area from size label
const sizeToSqFt = (size?: string): number | null => {
  if (!size) return null;
  const normalized = size.toLowerCase();
  if (normalized.includes('small')) return 500;
  if (normalized.includes('medium')) return 1500;
  if (normalized.includes('large')) return 4000;
  return null;
};

const budgetRangeFromPerSqFt = (budgetStr?: string, sizeLabel?: string) => {
  if (!budgetStr) return { text: '', totalRange: '' };
  const match = budgetStr.match(/\$?(\d+(?:\.\d+)?)\s*-\s*\$?(\d+(?:\.\d+)?)/);
  const perSq = match ? [parseFloat(match[1]), parseFloat(match[2])] : null;
  const area = sizeToSqFt(sizeLabel);
  if (perSq && area) {
    const minTotal = perSq[0] * area;
    const maxTotal = perSq[1] * area;
    return {
      text: `${budgetStr} (per sq ft)`,
      totalRange: `Approx total budget target: $${Math.round(minTotal).toLocaleString()} - $${Math.round(maxTotal).toLocaleString()} assuming ~${area.toLocaleString()} sq ft.`
    };
  }
  return { text: budgetStr, totalRange: '' };
};

export const generateLandscapeDesign = async (
  yardFile: File,
  styleFiles: File[],
  prompt: string,
  stylePreference: string,
  budget: string,
  locationType?: string,
  spaceSize?: string,
  onProgress?: (partialResult: Partial<GeneratedDesign>) => void,
  useRag: boolean = true,
  options?: { renderOnly?: boolean }
): Promise<GeneratedDesign> => {
  if (!GEMINI_API_KEY) {
    throw new Error("Gemini API key not found in environment variables");
  }

  const ai = new GoogleGenAI({ apiKey: GEMINI_API_KEY });

  // Convert files to base64
  const yardBase64 = await fileToGenericBase64(yardFile);
  const styleBase64Array: string[] = [];

  // Convert all style images to base64
  for (const styleFile of styleFiles) {
    const base64 = await fileToGenericBase64(styleFile);
    styleBase64Array.push(base64);
  }

  try {
    // -------------------------------------------------------------------------
    // PHASE 1: SCENE UNDERSTANDING & DESIGN INTENT (Pro Model)
    // -------------------------------------------------------------------------
    console.log("Phase 1: Scene Understanding");
    const analysisParts: any[] = [
      { inlineData: { mimeType: yardFile.type, data: yardBase64 } },
      { text: `[The User's Yard]` }
    ];

    if (styleFiles.length > 0) {
      styleFiles.forEach((styleFile, index) => {
        analysisParts.push({
          inlineData: { mimeType: styleFile.type, data: styleBase64Array[index] }
        });
        analysisParts.push({
          text: `[Style Reference Image ${index + 1}${styleFiles.length > 1 ? ` of ${styleFiles.length}` : ''}]`
        });
      });
    }

    const budgetDetails = budgetRangeFromPerSqFt(budget, spaceSize);
    analysisParts.push({
      text: `
      You are a Senior Landscape Architect.
      
      CONTEXT:
      - Location type: ${locationType || 'Not specified'}
      - Space size: ${spaceSize || 'Not specified'} ${sizeToSqFt(spaceSize) ? `(approx ${sizeToSqFt(spaceSize)?.toLocaleString()} sq ft)` : ''}
      - Style target: ${stylePreference}
      ${budget ? `- Budget: ${budgetDetails.text}${budgetDetails.totalRange ? `\n      - ${budgetDetails.totalRange}` : ''}` : ''}
      - User request: ${prompt || 'No extra notes'}
      
      PHASE 1 TASK: Analyze the yard image to create a strict Scene JSON and Design JSON.
      
      1. SCENE JSON (The Truth): Identify the FIXED geometry that must not change.
         Structure:
         {
           "house": { "footprint": "...", "windows": "..." },
           "fences": "...",
           "shed": { "exists": boolean, "location": "..." },
           "terrain": "...",
           "existingTrees": "..."
         }
      
      2. DESIGN JSON (The Changes): Apply the user's request in the specified style.
         Structure:
         {
           "newHardscape": "...",
           "newPlantings": "...",
           "furniture": "...",
           "budgetNotes": "${budget ? budgetDetails.totalRange || budget : 'not provided'}"
         }

      OUTPUT FORMAT: Provide a structured text response containing these two JSON blocks clearly labeled.
      Do NOT invent structures that aren't in the photo.
    `});

    const sceneUnderstandingRes = await withTimeout(
      retryOperation(() =>
        ai.models.generateContent({
          model: MODEL_REASONING,
          contents: { parts: analysisParts }
        })
      ),
      PHASE_TIMEOUT_MS,
      'Scene understanding'
    );

    const sceneContext = sceneUnderstandingRes.text || "";
    console.log("Scene Context Generated:", sceneContext.substring(0, 200) + "...");

    // -------------------------------------------------------------------------
    // PHASE 2: GENERATE 3D RENDER (Image Model)
    // -------------------------------------------------------------------------
    console.log("Phase 2: Generating Render");

    const renderPrompt = `
      Act as a Photorealist Landscape Renderer.
      INPUT: [The User's Yard] (The base geometry).

      SCENE DATA (SOURCE OF TRUTH):
      ${sceneContext}

      TASK: Overpaint this specific view to match the Design JSON described above.

      STRICT RULES:
      1. GEOMETRY ANCHORS: You MUST keep the house architecture, windows, and perimeter fences EXACTLY as they appear in the input photo. Do not move the camera.
      2. STYLE: ${stylePreference}. Photorealistic, high definition.
      3. LOCATION CONTEXT: ${locationType || 'Not specified'} | SIZE: ${spaceSize || 'Not specified'} ${sizeToSqFt(spaceSize) ? `(approx ${sizeToSqFt(spaceSize)?.toLocaleString()} sq ft)` : ''}
      ${budget ? `4. BUDGET GUIDANCE: ${budgetRangeFromPerSqFt(budget, spaceSize).totalRange || budgetRangeFromPerSqFt(budget, spaceSize).text}` : ''}
      3. Do NOT hallucinate new buildings.

      ADDITIONAL OUTPUT REQUIREMENT:
      After producing the render, output an additional JSON block describing EXACTLY what you added to the scene.
      Format:
      {
        "plants": ["list of specific plants with quantities, e.g., '5 Japanese Maples', '12 Lavender bushes'"],
        "hardscape": ["list of hardscape features with quantities, e.g., 'Stone patio 200 sqft', 'Gravel pathway 80 sqft'"],
        "features": ["list of features like 'Fire pit', 'Water fountain', 'Lighting fixtures'"],
        "structures": ["list of structures like 'Pergola', 'Arbor', 'Trellis'"],
        "furniture": ["list of outdoor furniture like 'Bench', '2 Lounge chairs'"],
        "labor": ["list of labor/installation tasks implied, e.g., 'Site preparation 400 sqft', 'Paver installation', 'Planting labor for 20 shrubs'"],
        "quantities": {
          "sod_sqft": 0,
          "mulch_sqft": 0,
          "gravel_sqft": 0,
          "pavers_sqft": 0
        }
      }

      Return this JSON directly in the text portion of the response after generating the image.
      Be specific and comprehensive - include EVERYTHING you added to transform the yard.
    `;

    const renderRes = await withTimeout(
      retryOperation(() =>
        ai.models.generateContent({
          model: MODEL_GENERATION,
          contents: {
            parts: [
              { inlineData: { mimeType: yardFile.type, data: yardBase64 } },
              { text: renderPrompt }
            ]
          }
        })
      ),
      PHASE_TIMEOUT_MS,
      'Render generation'
    );

    const renderImage = extractImage(renderRes);

    if (!renderImage) {
      throw new Error("Failed to generate render image");
    }
    const renderBase64Raw = renderImage.split(',')[1];

    // Extract design JSON from text response
    let designJSON: any = null;
    try {
      const renderText = renderRes.text || "";
      console.log("Render response text:", renderText.substring(0, 500));

      // Try to extract JSON from the response
      const jsonMatch = renderText.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        designJSON = JSON.parse(jsonMatch[0]);
        console.log("✅ Design JSON extracted from render:", JSON.stringify(designJSON, null, 2));
      } else {
        console.warn("⚠️ No JSON block found in render response");
      }
    } catch (error) {
      console.warn("⚠️ Failed to extract design JSON from render:", error);
    }

    // EMIT PARTIAL RESULT: Render is ready!
    if (onProgress) {
      onProgress({
        renderImages: [renderImage],
        // We can emit empty/loading states for others if needed, or just omit them
        // The UI should handle missing fields gracefully
      });
    }

    // If renderOnly is requested, return early with render image only
    if (options?.renderOnly) {
      return {
        analysis: {
          currentLayout: "Scene Analyzed",
          designConcept: `${stylePreference} concept`,
          visualDescription: "See render",
          maintenanceLevel: "Medium",
        },
        estimates: {
          totalCost: 0,
          currency: "USD",
          breakdown: [],
          plantPalette: [],
          ragEnhanced: false,
        },
        renderImages: [renderImage],
        planImage: "",
        designJSON: designJSON,
      };
    }

    // -------------------------------------------------------------------------
    // PHASE 3: GENERATE 2D PLAN (Image Model)
    // -------------------------------------------------------------------------
    console.log("Phase 3: Generating Plan");

    const planPrompt = `
      Generate a 2D LANDSCAPING MAP based on the provided yard design image.
      
      THIS IS STRICTLY A 2D TOP-DOWN MAP:
      - Pure bird's-eye view looking straight down from above
      - Flat 2D technical drawing style - NOT a photo, NOT 3D
      - Clean architectural site plan aesthetic
      
      MAP ELEMENTS TO INCLUDE:
      - Property boundaries (dashed lines)
      - House/building footprint (outlined rectangle)
      - All paths, patios, driveways (shown with pattern fills)
      - Lawn and garden bed areas (organic shapes)
      - Trees shown as circles from above
      - Shrubs shown as smaller circles/clusters
      - Any water features (pools, fountains) shown as shapes
      - North arrow symbol
      - Scale bar
      
      VISUAL STYLE:
      - White/cream background
      - Light green for lawn areas
      - Darker greens for trees and plantings
      - Gray for hardscape/pavers
      - Blue for water features
      - Black outlines for structures
      
      DO NOT INCLUDE:
      - Any 3D perspective or shadows
      - Any photorealistic elements
      - Any decorative borders or frames
      
      Output a clean, professional 2D landscaping site map.
    `;

    const planPromise = ai.models.generateContent({
      model: MODEL_GENERATION,
      contents: {
        parts: [
          { inlineData: { mimeType: "image/png", data: renderBase64Raw } },
          { text: planPrompt }
        ]
      }
    });

    // -------------------------------------------------------------------------
    // PHASE 4: COST & QUANTITY ANALYSIS (Pro Model)
    // -------------------------------------------------------------------------
    // -------------------------------------------------------------------------
    // PHASE 4: COST & QUANTITY ANALYSIS (Pro Model)
    // -------------------------------------------------------------------------
    console.log("Phase 4: Cost Analysis");

    const analysisPrompt = `
      Act as a Senior Quantity Surveyor specializing in landscape architecture.

      Your task:
      Analyze the rendered image and the design context to produce a DETAILED QUANTITY TAKEOFF with PRICING in STRICT JSON format.
      
      TASK: 
      1. VISUAL IDENTIFICATION: Scan the image and list every distinct material and plant group.
      2. SCOPE VERIFICATION: Compare the DESIGN image against the ORIGINAL image context.
         - Identify elements that are EXISTING (e.g., original fences, retaining walls, mature trees, house siding).
         - Identify elements that are NEW or MODIFIED (e.g., new pavers, new planting beds, renovated structures).
      3. ESTIMATION: Estimate the area (sq ft) or count (qty) ONLY for NEW or MODIFIED scope. 
         - DO NOT price existing elements unless they were explicitly flagged for removal/replacement. 
         - Explicitly exclude cost for existing fences, slabs, or structures.
      4. PRICING: Apply realistic US market rates (materials + installation) for the new scope.
      ${budget ? `5. BUDGET CHECK: The user's target budget is \"${budget}\". If the total exceeds this, suggest cost-saving alternatives.` : ''}
      6. LABOR: You MUST include a separate line item for \"Labor & Installation\" (typically 30-50% of material costs).
      7. TOTAL COST: Calculate and include the totalCost as the sum of all line items.
      
      RETURN JSON ONLY. NO TEXT.

      SCHEMA:
      {
        "designConcept": "string - brief design description",
        "visualDescription": "string - detailed scene description",
        "maintenanceLevel": "Low | Medium | High",
        "totalCost": number,
        "materials": [
          {
            "name": "string (e.g. 'Japanese Maple' or 'Paver Patio')",
            "quantity": "string (e.g. '3 plants' or '200 sqft')",
            "unitCost": "string (e.g. '$45/plant' or '$12/sqft')",
            "totalCost": "string (e.g. '$135' or '$2,400')",
            "notes": "string (e.g. 'Acer palmatum, 5-gallon container' or 'Natural stone pavers with installation')",
            "category": "Plants | Hardscape | Features | Structures | Furniture | Labor"
          }
        ],
        "plants": [
          { "name": "string", "quantity": number, "description": "string" }
        ],
        "hardscape": [
          { "name": "string", "quantity": number, "description": "string" }
        ],
        "features": [
          { "name": "string", "quantity": number, "description": "string" }
        ],
        "structures": [
          { "name": "string", "quantity": number, "description": "string" }
        ],
        "furniture": [
          { "name": "string", "quantity": number, "description": "string" }
        ]
      }

      CRITICAL RULES:
      - EXCLUDE EXISTING: Do not price items that clearly existed in the original yard (e.g. existing fences, concrete slabs) unless modified.
      - EXISTING ≠ SCOPE: Just because it's in the picture doesn't mean it's being built. Only price the DELTA (changes).
      - Every item in "materials" array MUST have realistic pricing (unitCost and totalCost).
      - totalCost at the root MUST be the sum of all materials[].totalCost (parse the numeric values).
      - Be precise with plant names (e.g., "Agave attenuata" instead of just "Agave").
      - Include installation/labor costs for each applicable item.
      - All costs should be realistic for 2024 US market rates.
    `;

    const analysisPromise = ai.models.generateContent({
      model: MODEL_REASONING,
      contents: {
        parts: [
          { inlineData: { mimeType: "image/png", data: renderBase64Raw } },
          { text: analysisPrompt }
        ]
      },
      config: {
        responseMimeType: "application/json",
      }
    });

    // Wait for both Plan and Analysis (with retry for transient errors)
    const [planRes, analysisRes] = await withTimeout(
      retryOperation(() => Promise.all([planPromise, analysisPromise])),
      PHASE_TIMEOUT_MS,
      'Plan and analysis generation'
    );

    const planImage = extractImage(planRes);
    if (!planImage) {
      throw new Error("Failed to generate plan image");
    }
    const planBase64Raw = planImage.split(',')[1];
    const planImageUri = `data:image/png;base64,${planBase64Raw}`;
    const jsonText = analysisRes.text || "{}";
    const data = JSON.parse(jsonText);

    // -------------------------------------------------------------------------
    // PHASE 5: RAG ENHANCEMENT (Optional)
    // -------------------------------------------------------------------------
    let plantPalette: any[] = [];
    let ragEnhanced = false;

    if (useRag) {
      try {
        const ragApiBase =
          import.meta.env.VITE_RAG_API_BASE_URL ||
          process.env.RAG_API_BASE_URL ||
          "http://localhost:8002";
        const ragUrl = `${ragApiBase.replace(/\/$/, "")}/api/enhance-with-rag`;
        console.log("Phase 5: RAG Enhancement");
        const ragResponse = await fetch(ragUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(data) // Send the structured data directly
        });

        if (ragResponse.ok) {
          const ragData = await ragResponse.json();
          plantPalette = ragData.plantPalette || [];
          ragEnhanced = ragData.rag_enhanced || false;
          console.log(`✅ RAG Enhancement: Found ${plantPalette.length} plants in catalog`);
          if (ragData.labor && ragData.labor.length) {
            console.log(`✅ RAG Enhancement: Found ${ragData.labor.length} structured labor items from components collection`);
            // store for later use in estimates
            (window as any).__ragLabor = ragData.labor; // lightweight bridge for now
          }
          if (ragData.hardscape && ragData.hardscape.length) {
            console.log(`✅ RAG Enhancement: Found ${ragData.hardscape.length} hardscape items`);
          }
        } else {
          console.warn("RAG Enhancement failed, continuing without it");
        }
      } catch (error) {
        console.warn("RAG Enhancement unavailable:", error);
      }
    } else {
      console.log("Phase 5: RAG Enhancement skipped (disabled by user)");
    }

    const finalResult: GeneratedDesign = {
      analysis: {
        currentLayout: "Scene Analyzed",
        designConcept: data.designConcept || `A ${stylePreference} transformation`,
        visualDescription: data.visualDescription || "See 3D Render",
        maintenanceLevel: data.maintenanceLevel || "Medium",
      },
      estimates: {
        totalCost: (() => {
          // If totalCost is provided by the API, use it
          if (data.totalCost && data.totalCost > 0) {
            return data.totalCost;
          }

          // Otherwise, calculate it from materials breakdown
          if (data.materials && Array.isArray(data.materials)) {
            const sum = data.materials.reduce((acc: number, item: any) => {
              const totalCostStr = item.totalCost || "0";
              const numericValue = parseFloat(totalCostStr.replace(/[^0-9.]/g, '')) || 0;
              return acc + numericValue;
            }, 0);
            return sum > 0 ? sum : 15000; // Fallback to a reasonable estimate
          }

          // Last resort fallback
          return 15000;
        })(),
        currency: "USD",
        breakdown: (data.materials && Array.isArray(data.materials) && data.materials.length > 0)
          ? data.materials.map((item: any) => ({
            name: item.name || "Unknown Item",
            quantity: item.quantity || "1",
            unitCost: item.unitCost || "$0",
            totalCost: item.totalCost || "$0",
            notes: item.notes || item.description || "",
            category: item.category || "Other"
          }))
          : [
            // Fallback breakdown if materials array is missing or empty
            ...(data.plants || []).map((p: any) => ({
              name: p.name,
              quantity: `${p.quantity || 1}`,
              unitCost: "$50/plant",
              totalCost: `$${(p.quantity || 1) * 50}`,
              notes: p.description || "",
              category: 'Plants'
            })),
            ...(data.hardscape || []).map((h: any) => ({
              name: h.name,
              quantity: `${h.quantity || 100} sqft`,
              unitCost: "$12/sqft",
              totalCost: `$${(h.quantity || 100) * 12}`,
              notes: h.description || "",
              category: 'Hardscape'
            })),
            ...(data.features || []).map((f: any) => ({
              name: f.name,
              quantity: `${f.quantity || 1}`,
              unitCost: "$200/item",
              totalCost: `$${(f.quantity || 1) * 200}`,
              notes: f.description || "",
              category: 'Features'
            })),
            ...(data.structures || []).map((s: any) => ({
              name: s.name,
              quantity: `${s.quantity || 1}`,
              unitCost: "$500/item",
              totalCost: `$${(s.quantity || 1) * 500}`,
              notes: s.description || "",
              category: 'Structures'
            })),
            ...(data.furniture || []).map((f: any) => ({
              name: f.name,
              quantity: `${f.quantity || 1}`,
              unitCost: "$150/item",
              totalCost: `$${(f.quantity || 1) * 150}`,
              notes: f.description || "",
              category: 'Furniture'
            })),
            // Prefer structured labor from the components collection (RAG) when available.
            // Falls back to a single placeholder labor line (the old behavior).
            ...(
              (window as any).__ragLabor && (window as any).__ragLabor.length
                ? (window as any).__ragLabor.map((l: any) => ({
                    name: l.common_name || l.name || "Labor Item",
                    quantity: `${l.quantity || 1}`,
                    unitCost: l.unit_price || l.unitCost || "TBD",
                    totalCost: l.total_estimate || l.totalCost || "TBD",
                    notes: l.notes || l.description || "From structured components catalog",
                    category: 'Labor'
                  }))
                : [{
                    name: "Labor & Installation",
                    quantity: "1",
                    unitCost: "$5,000",
                    totalCost: "$5,000",
                    notes: "Professional installation and labor costs (consider enabling RAG components for structured labor)",
                    category: 'Labor'
                  }]
            )
          ],
        plantPalette,
        ragEnhanced,
      },
      renderImages: [renderImage],
      planImage: planImageUri,
      designJSON: designJSON, // Include the design specification from Phase 2
    };

    // Final emit
    if (onProgress) {
      onProgress(finalResult);
    }

    return finalResult;

  } catch (error) {
    console.error("Gemini Generation Error:", error);
    throw error;
  }
};

export interface Annotation {
  type: 'circle' | 'pen';
  x: number;
  y: number;
  radius?: number;
  path?: { x: number; y: number }[];
  description: string;
  color: string;
}

export const analyzeAndRegenerateDesign = async (
  originalRenderImage: string, // Base64 data URI or URL
  annotatedImage: string, // Base64 data URI with user annotations
  annotations: Annotation[],
  originalYardImage?: File | null
): Promise<string> => {
  if (!GEMINI_API_KEY) {
    throw new Error("Gemini API key not found in environment variables");
  }

  const ai = new GoogleGenAI({ apiKey: GEMINI_API_KEY });

  // Helper to convert any image source to base64
  const imageToBase64 = async (imageSource: string): Promise<string> => {
    // If it's already a data URI, extract the base64 part
    if (imageSource.startsWith('data:')) {
      const base64 = imageSource.split(',')[1];
      if (!base64) {
        throw new Error('Invalid data URI format');
      }
      return base64;
    }

    // If it's a URL (http/https or blob), fetch and convert
    if (imageSource.startsWith('http') || imageSource.startsWith('blob:')) {
      try {
        const response = await fetch(imageSource);
        const blob = await response.blob();
        return new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => {
            const result = reader.result as string;
            const base64 = result.split(',')[1];
            if (!base64) {
              reject(new Error('Failed to extract base64 from blob'));
              return;
            }
            resolve(base64);
          };
          reader.onerror = () => reject(new Error('Failed to read blob'));
          reader.readAsDataURL(blob);
        });
      } catch (error) {
        console.error('Error fetching image from URL:', error);
        throw new Error(`Failed to fetch image from URL: ${imageSource.substring(0, 50)}...`);
      }
    }

    // Assume it's raw base64
    return imageSource;
  };

  try {
    // Convert images to base64, handling different formats
    console.log("Converting images to base64...");
    console.log("  Original render source type:", originalRenderImage.substring(0, 30));
    console.log("  Annotated image source type:", annotatedImage.substring(0, 30));

    const originalBase64 = await imageToBase64(originalRenderImage);
    const annotatedBase64 = await imageToBase64(annotatedImage);

    console.log("  Original base64 length:", originalBase64.length);
    console.log("  Annotated base64 length:", annotatedBase64.length);

    // Validate the base64 strings
    if (originalBase64.length < 1000) {
      throw new Error('Original render image appears to be too small or corrupted');
    }
    if (annotatedBase64.length < 1000) {
      throw new Error('Annotated image appears to be too small or corrupted');
    }

    // Prepare annotations description
    const annotationsText = annotations.map((ann, idx) => {
      if (ann.type === 'circle') {
        return `Annotation ${idx + 1} (Circle): Located at coordinates (${Math.round(ann.x)}, ${Math.round(ann.y)}) with radius ${Math.round(ann.radius || 0)}. User wants: "${ann.description}"`;
      } else {
        return `Annotation ${idx + 1} (Pen/Drawing): Path drawn by user. User wants: "${ann.description}"`;
      }
    }).join('\n');

    // Phase 1: Analyze the annotated image to understand what needs to change
    console.log("Phase 1: Analyzing annotations");
    const analysisPrompt = `
      You are a Senior Landscape Architect analyzing user annotations on a landscape design render.
      
      CRITICAL ANALYSIS APPROACH - Follow this two-step process:
      
      STEP 1: UNDERSTAND THE ENTIRE IMAGE CONTEXT FIRST
      - Examine the complete landscape design render to understand the overall design style, theme, and aesthetic
      - Identify the overall color palette, materials, and design language used throughout
      - Note the spatial relationships, proportions, and flow of the entire design
      - Understand the context of surrounding elements (house, fences, pathways, existing features)
      - Recognize the lighting conditions, time of day, and atmosphere of the scene
      
      STEP 2: FOCUS ON THE ANNOTATED AREAS WITHIN CONTEXT
      - Now examine the specific annotated areas (circles or drawn paths) marked by the user
      - Identify what currently exists in each annotated location
      - Understand how each annotated area relates to and fits within the overall design context
      - Consider how changes in the annotated areas will affect the visual harmony of the entire scene
      
      ANNOTATIONS:
      ${annotationsText}
      
      TASK: Create a comprehensive modification plan that:
      1. First establishes the full design context (style, materials, colors, spatial relationships)
      2. Then identifies what currently exists in each annotated area
      3. Determines what should replace or be added based on:
         - The user's description for each annotation
         - How it will integrate with the surrounding design elements
         - How it maintains or enhances the overall design coherence
         - How it respects the existing style and aesthetic
      
      OUTPUT: Provide a detailed, structured description with two sections:
      
      SECTION 1 - FULL CONTEXT ANALYSIS:
      - Overall design style and aesthetic (e.g., "Modern Minimalist with clean lines and neutral tones")
      - Dominant materials and textures throughout the scene
      - Color palette and visual harmony
      - Spatial relationships and flow
      - Lighting and atmosphere
      
      SECTION 2 - ANNOTATED AREA MODIFICATIONS:
      For each annotation listed above, provide:
      - Exact location within the scene (e.g., "in the center of the yard, between the patio and the fence")
      - Current elements in that area (e.g., "grass lawn with small shrubs")
      - Relationship to surrounding elements (e.g., "adjacent to the stone patio and near the house foundation")
      - Desired changes based on the user's description for that annotation
      - How the modification will integrate with the overall design
      - Specific materials, plants, or features to add/change that match the overall aesthetic
      
      Be extremely specific about how each change will look and feel within the context of the entire design.
      Ensure that modifications in annotated areas feel natural and cohesive with the rest of the landscape.
    `;

    const analysisParts: any[] = [
      { inlineData: { mimeType: "image/png", data: annotatedBase64 } },
      { text: `[Annotated Render - User has marked areas to change]` },
      { inlineData: { mimeType: "image/png", data: originalBase64 } },
      { text: `[Original Render - Reference for what currently exists]` },
      { text: analysisPrompt }
    ];

    // If we have the original yard image, include it for context
    if (originalYardImage) {
      const yardBase64 = await fileToGenericBase64(originalYardImage);
      analysisParts.splice(2, 0,
        { inlineData: { mimeType: originalYardImage.type, data: yardBase64 } },
        { text: `[Original Yard Photo - For reference]` }
      );
    }

    const analysisRes = await ai.models.generateContent({
      model: MODEL_REASONING,
      contents: { parts: analysisParts }
    });

    const modificationPlan = analysisRes.text || "";
    console.log("Modification Plan:", modificationPlan);

    // Phase 2: Generate new render with modifications
    console.log("Phase 2: Generating modified render");
    const generationPrompt = `
      Act as a Photorealist Landscape Renderer.
      
      TASK: Modify the provided landscape render according to the user's requested changes.
      
      ORIGINAL RENDER: The first image shows the current design.
      ANNOTATED RENDER: The second image shows where the user wants changes (marked with red circles/drawings).
      MODIFICATION PLAN: ${modificationPlan}
      
      INSTRUCTIONS:
      1. Keep ALL elements that are NOT in the annotated areas exactly as they are
      2. Apply the modifications ONLY to the areas marked by the user
      3. Maintain the same style, lighting, and overall aesthetic as the original render
      4. Ensure the modifications blend seamlessly with the rest of the design
      5. Keep the same camera angle and perspective
      6. Maintain photorealistic quality
      
      CRITICAL RULES:
      - Do NOT change anything outside the annotated areas
      - Do NOT move or modify the house, fences, or other fixed structures
      - The modifications should look natural and integrated
      - Preserve the original design's style and quality
    `;

    const generationParts: any[] = [
      { inlineData: { mimeType: "image/png", data: originalBase64 } },
      { text: `[Original Render]` },
      { inlineData: { mimeType: "image/png", data: annotatedBase64 } },
      { text: `[Annotated Render with User Markings]` },
      { text: generationPrompt }
    ];

    const renderRes = await ai.models.generateContent({
      model: MODEL_GENERATION,
      contents: { parts: generationParts }
    });

    const newRenderImage = extractImage(renderRes);
    if (!newRenderImage) {
      throw new Error("Failed to generate modified render image");
    }

    console.log("✅ Modified render generated successfully");
    return newRenderImage;

  } catch (error) {
    console.error("Edit Mode Generation Error:", error);
    throw error;
  }
};
