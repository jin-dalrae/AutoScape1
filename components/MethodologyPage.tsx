import React from 'react';
import { useNavigate } from 'react-router-dom';

export const MethodologyPage: React.FC = () => {
  const navigate = useNavigate();

  const steps = [
    {
      number: "01",
      title: "Visual Generation",
      description: "We generate a photorealistic 'ideal backyard' image using a hybrid of visual RAG (searching our curated landscaping image collection for style and material references) + advanced image models (Gemini + Freepik). This gives you the creative vision first.",
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      ),
      highlight: "Visual RAG collection (inspiration + photo realism)"
    },
    {
      number: "02",
      title: "Structured Component Extraction",
      description: "Gemini vision + structured prompting analyzes the generated image (and your inputs) to extract precise components: plants with quantities, hardscape (pavers, gravel, walls), features, structures, furniture — and now explicitly labor tasks (site prep, installation, grading, etc.).",
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2m0-2a2 2 0 012-2m-2 2v2m0-2a2 2 0 01-2-2m2 2a2 2 0 012 2" />
        </svg>
      ),
      highlight: "Includes labor as first-class extracted items"
    },
    {
      number: "03",
      title: "RAG-Powered Component Lookup",
      description: "We search our dedicated autoscape-components collection in Qdrant. This is a clean, curated vector database (separate from the visual photo library) containing plants, hardscape, materials, and labor — each with component_type, botanical/category data, units, realistic price ranges, tags, and reference images.",
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 01-14 0 7 7 0 0114 0z" />
        </svg>
      ),
      highlight: "component_type filter: plant | hardscape | labor | material"
    },
    {
      number: "04",
      title: "Accurate Budget Assembly",
      description: "The RAG enhancement API returns enriched items with verified pricing pulled directly from the structured collection. We combine material costs + installation/labor (now properly itemized instead of a vague 30-50% guess), quantities, and produce transparent line items, PlantPalette, and total estimates.",
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 4.01V8" />
        </svg>
      ),
      highlight: "Labor is now queryable & grounded like everything else"
    }
  ];

  const collections = [
    {
      name: "Visual Inspiration Collection",
      id: "autoscape landscaping (or freepik_landscaping)",
      purpose: "Product photos, textures, and scene references. Used during image generation for style matching and realistic material visuals.",
      tech: "CLIP vision + text embeddings, fast similarity search",
      color: "indigo"
    },
    {
      name: "Structured Components Collection",
      id: "autoscape-components",
      purpose: "Curated, typed data for accurate pricing & specs. Plants (with botanical names + zones), hardscape, materials, and labor. Powers budgets and palettes with real unit costs.",
      tech: "Text embeddings + payload filters (component_type, category). FastEmbed + Qdrant indexes.",
      color: "emerald"
    }
  ];

  const laborItems = [
    "Site Preparation & Demolition",
    "Grading & Excavation",
    "Plant Installation Labor",
    "Hardscape Installation",
    "Irrigation & Drainage Install",
    "Final Cleanup & Finish Grade",
    "Project Management & Permits"
  ];

  return (
    <div className="min-h-screen bg-white" style={{ fontFamily: `'Montserrat', system-ui, sans-serif` }}>
      {/* Hero */}
      <div className="relative bg-gradient-to-br from-emerald-900 via-green-800 to-teal-900 text-white py-20 px-6">
        <div className="max-w-5xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur px-4 py-1 rounded-full text-sm tracking-[2px] mb-6">
            TRANSPARENT BY DESIGN
          </div>
          <h1 className="text-6xl md:text-7xl font-light tracking-tighter mb-6">
            Our Methodology
          </h1>
          <p className="text-2xl text-emerald-100 max-w-3xl mx-auto font-light leading-tight">
            How AutoScape turns a photo + concept into a beautiful render<br />and a genuinely useful, itemized budget.
          </p>
          <div className="mt-10 flex flex-wrap justify-center gap-4">
            <button
              onClick={() => navigate('/create')}
              className="px-8 py-3.5 bg-white text-emerald-900 font-medium rounded-2xl hover:bg-emerald-50 transition-all flex items-center gap-2"
            >
              Try the generator →
            </button>
            <button
              onClick={() => navigate('/about')}
              className="px-8 py-3.5 border border-white/60 hover:bg-white/10 rounded-2xl transition-all"
            >
              About the studio
            </button>
          </div>
        </div>
      </div>

      {/* The Core Idea */}
      <div className="max-w-5xl mx-auto px-6 pt-16 pb-12">
        <div className="text-center mb-12">
          <div className="uppercase tracking-[3px] text-emerald-600 text-xs font-semibold mb-3">THE PROBLEM WE SOLVE</div>
          <h2 className="text-4xl font-light text-gray-900 tracking-tight">Beautiful images are easy.<br />Accurate budgets are hard.</h2>
        </div>

        <div className="grid md:grid-cols-3 gap-6 text-sm">
          <div className="bg-gray-50 rounded-3xl p-7">
            <div className="font-semibold text-gray-900 mb-2">Traditional AI generators</div>
            <p className="text-gray-600 leading-relaxed">Produce pretty pictures but invent pricing or use vague "30-50% labor" rules. Especially weak on installation and site work.</p>
          </div>
          <div className="bg-gray-50 rounded-3xl p-7">
            <div className="font-semibold text-gray-900 mb-2">Pure product scrapers</div>
            <p className="text-gray-600 leading-relaxed">Give you prices but no design intelligence. No understanding of how components work together in a real yard.</p>
          </div>
          <div className="bg-emerald-50 border border-emerald-100 rounded-3xl p-7">
            <div className="font-semibold text-emerald-900 mb-2">AutoScape hybrid approach</div>
            <p className="text-emerald-700 leading-relaxed">Creative vision from visual AI + real, filterable, typed pricing data from a dedicated components vector database. Labor included.</p>
          </div>
        </div>
      </div>

      {/* The Pipeline */}
      <div className="bg-gray-950 text-white py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <div className="uppercase tracking-[3px] text-emerald-400 text-xs font-semibold mb-3">END-TO-END PIPELINE</div>
            <h3 className="text-4xl font-light tracking-tight">Generate → Extract → Lookup → Budget</h3>
          </div>

          <div className="space-y-8">
            {steps.map((step, index) => (
              <div key={index} className="flex flex-col md:flex-row gap-8 md:gap-12 border-l-2 border-emerald-500/30 md:border-l-0 pl-6 md:pl-0">
                <div className="md:w-16 flex-shrink-0">
                  <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center text-2xl font-light tracking-tighter">
                    {step.number}
                  </div>
                </div>
                <div className="flex-1">
                  <div className="flex items-start gap-4 mb-3">
                    <div className="mt-1 text-emerald-400">{step.icon}</div>
                    <h4 className="text-2xl font-light tracking-tight">{step.title}</h4>
                  </div>
                  <p className="text-gray-300 text-[15px] leading-relaxed max-w-3xl">{step.description}</p>
                  <div className="mt-3 inline-block text-xs uppercase tracking-widest bg-emerald-900/40 text-emerald-400 px-3 py-1 rounded">
                    {step.highlight}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Two Collections Architecture */}
      <div className="max-w-5xl mx-auto px-6 py-16">
        <div className="text-center mb-10">
          <div className="uppercase tracking-[3px] text-emerald-600 text-xs font-semibold mb-3">KEY ARCHITECTURAL DECISION</div>
          <h3 className="text-3xl font-light tracking-tight text-gray-900">We deliberately use two different Qdrant collections</h3>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {collections.map((col, i) => (
            <div key={i} className={`rounded-3xl p-8 border ${i === 1 ? 'border-emerald-200 bg-emerald-50/50' : 'border-gray-200 bg-white'}`}>
              <div className="uppercase text-xs tracking-[2px] text-gray-500 mb-1">{col.name}</div>
              <div className="font-mono text-sm text-emerald-700 mb-4">{col.id}</div>
              <p className="text-gray-700 leading-relaxed mb-6">{col.purpose}</p>
              <div className="text-xs text-gray-500">
                <span className="font-medium text-gray-600">How we use it:</span> {col.tech}
              </div>
            </div>
          ))}
        </div>

        <p className="mt-8 text-sm text-center text-gray-500 max-w-lg mx-auto">
          The visual collection makes things look real. The components collection makes the numbers honest.
        </p>
      </div>

      {/* Labor Spotlight */}
      <div className="bg-white border-y py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center gap-4 mb-6">
            <div className="px-4 py-1 bg-emerald-100 text-emerald-700 text-xs tracking-[1.5px] rounded font-semibold">NEW</div>
            <h4 className="text-3xl font-light tracking-tight">Labor is now a structured component</h4>
          </div>
          <p className="text-gray-600 max-w-3xl mb-8">
            Previously labor was just a vague percentage or a single $5,000 line item. Now we extract specific labor tasks during generation and look them up in the same components database.
          </p>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            {laborItems.map((item, idx) => (
              <div key={idx} className="flex items-center gap-3 bg-gray-50 rounded-2xl px-5 py-3.5 border border-gray-100">
                <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full flex-shrink-0" />
                <span>{item}</span>
              </div>
            ))}
          </div>

          <div className="mt-6 text-xs text-emerald-700">
            Each has proper units (per sq ft, per plant, percent, lump sum) and realistic market ranges pulled from the same RAG system as plants and pavers.
          </div>
        </div>
      </div>

      {/* Why it matters */}
      <div className="max-w-5xl mx-auto px-6 py-16">
        <div className="grid md:grid-cols-3 gap-x-8 gap-y-12">
          {[
            { title: "Honest pricing", text: "Prices come from a maintainable, curated database — not the model making things up on the fly." },
            { title: "Actionable breakdowns", text: "You see exactly what each plant, paver, and labor task costs. Great for contractors and phased projects." },
            { title: "Extensible", text: "Adding new plants, hardscape, or labor rates is as simple as upserting new points into the components collection." }
          ].map((item, i) => (
            <div key={i}>
              <div className="font-medium text-lg tracking-tight mb-2 text-gray-900">{item.title}</div>
              <p className="text-gray-600 leading-relaxed">{item.text}</p>
            </div>
          ))}
        </div>
      </div>

      {/* CTA */}
      <div className="bg-emerald-950 text-white py-14 px-6">
        <div className="max-w-xl mx-auto text-center">
          <p className="uppercase tracking-[3px] text-emerald-400 text-xs mb-3">Ready to see it in action?</p>
          <h3 className="text-3xl font-light tracking-tighter mb-8">Generate a design and get a real budget.</h3>
          <button
            onClick={() => navigate('/create')}
            className="inline-flex items-center gap-3 bg-white hover:bg-emerald-100 transition-colors text-emerald-950 font-medium px-10 py-4 rounded-2xl text-base"
          >
            Start a new project
            <span aria-hidden>→</span>
          </button>
          <div className="mt-4 text-emerald-400 text-sm">Free tier available • No credit card required</div>
        </div>
      </div>

      {/* Footer note */}
      <div className="text-center py-8 text-[10px] text-gray-400 tracking-widest">
        BUILT WITH QDRANT • GEMINI • FASTEMBED • FREEPIC
      </div>
    </div>
  );
};

export default MethodologyPage;
