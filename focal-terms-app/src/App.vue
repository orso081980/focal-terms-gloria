<template>
  <div class="min-h-screen bg-slate-50 text-slate-800 font-sans">
    <!-- Header -->
    <header class="bg-indigo-900 text-white px-6 py-5 shadow-lg">
      <h1 class="text-2xl font-bold tracking-tight">Focal Terms Explorer — Gloria Dataset</h1>
      <p class="text-indigo-300 text-sm mt-1"> Patent ↔ Science knowledge transfer · biomedical entity overlap analysis </p>
    </header>

    <!-- Tab navigation -->
    <nav class="bg-white border-b border-slate-200 sticky top-0 z-10">
      <div class="max-w-7xl mx-auto px-4 flex overflow-x-auto">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          :class="[
            'px-5 py-3.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap',
            activeTab === tab.id ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-500 hover:text-slate-700',
          ]"
        >
          {{ tab.label }}
        </button>
      </div>
    </nav>

    <main class="max-w-7xl mx-auto px-4 py-6 space-y-6">
      <!-- ─────────────────────────────────────────────────────
           TAB: Overview
           Powered by viewer_data_full.json
      ──────────────────────────────────────────────────────── -->
      <template v-if="activeTab === 'overview'">
        <div v-if="loadingViewer" class="text-center py-16 text-slate-400 text-sm">Loading overview…</div>
        <div v-else-if="errorViewer" class="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm"> ⚠️ {{ errorViewer }} </div>
        <template v-else-if="viewer">
          <!-- Stat cards -->
          <section class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Total focal pairs" :value="fmt(viewer.summary.total_focal_pairs)" />
            <StatCard label="Patents with focal terms" :value="fmt(viewer.summary.unique_patents)" />
            <StatCard label="Unique focal terms" :value="fmt(viewer.summary.unique_terms)" />
            <StatCard label="Median terms / patent" :value="viewer.summary.median_terms_per_patent" />
          </section>

          <!-- Charts row -->
          <section class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
              <h2 class="text-sm font-semibold text-slate-600 mb-4">Top 20 focal terms — by patent count</h2>
              <div class="h-80">
                <ChartWidget type="bar" :data="topTermsChart" :options="horizBarOpts" />
              </div>
            </div>
            <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
              <h2 class="text-sm font-semibold text-slate-600 mb-4">Distribution — focal terms per patent</h2>
              <div class="h-80">
                <ChartWidget type="bar" :data="distChart" :options="distOpts" />
              </div>
            </div>
          </section>

          <!-- Semantic mini-summary -->
          <section v-if="viewer.similarity" class="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
            <h2 class="text-sm font-semibold text-slate-600 mb-4">
              Semantic similarity snapshot
              <span class="ml-2 text-xs font-normal text-slate-400">(Step 3 — 20 k sampled pairs)</span>
            </h2>
            <div class="grid grid-cols-3 md:grid-cols-6 gap-4 text-center">
              <div v-for="s in simCards" :key="s.label">
                <div class="text-xl font-bold text-purple-600">{{ s.value }}</div>
                <div class="text-xs text-slate-500 mt-0.5">{{ s.label }}</div>
              </div>
            </div>
          </section>

          <!-- Pipeline explanation -->
          <section class="bg-slate-100 rounded-xl p-5 space-y-3">
            <h2 class="font-semibold text-slate-700">How the pipeline works</h2>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-slate-600">
              <div class="bg-white rounded-lg p-4 border border-indigo-100">
                <p class="font-semibold text-indigo-700 mb-1">Step 1 — Identify focal terms</p>
                <p>Load patent terms, clean the patent–paper link table, load paper terms, then inner-join on <code class="bg-slate-50 px-1 rounded text-xs">(patent_id, term)</code>. Any term present in both a patent and a cited paper is a focal term. Output columns: <code class="bg-slate-50 px-1 rounded text-xs">freq_in_patent</code> and <code class="bg-slate-50 px-1 rounded text-xs">freq_in_cited_paper</code>.</p>
              </div>
              <div class="bg-white rounded-lg p-4 border border-emerald-100">
                <p class="font-semibold text-emerald-700 mb-1">Step 2 — Measure overlap intensity</p>
                <p>Count unique focal terms per patent, compute summary statistics (mean, median, std, min, max), produce a histogram and KDE density plot, and rank patents and terms by overlap.</p>
              </div>
              <div class="bg-white rounded-lg p-4 border border-purple-100">
                <p class="font-semibold text-purple-700 mb-1">Step 3 — Semantic context comparison</p>
                <p>For 20,000 pairs: build co-occurring term contexts, serialise to sentences anchored by the focal term, encode with <code class="bg-slate-50 px-1 rounded text-xs">all-MiniLM-L6-v2</code>, compare via cosine similarity.</p>
              </div>
            </div>
          </section>

          <!-- Top 10 patents + Most used terms (from Step 2 data) -->
          <template v-if="step2">
            <section class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
                <h2 class="text-sm font-semibold text-slate-600 mb-4">Top 10 patents by focal-term count</h2>
                <table class="w-full text-sm">
                  <thead class="bg-slate-50">
                    <tr>
                      <th class="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">#</th>
                      <th class="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Patent ID</th>
                      <th class="px-3 py-2 text-right text-xs font-semibold text-slate-500 uppercase">Focal terms</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="(p, i) in step2.top_10_patents"
                      :key="p.patent_id"
                      class="border-t border-slate-100 hover:bg-indigo-50 transition-colors"
                    >
                      <td class="px-3 py-2 text-slate-400">{{ i + 1 }}</td>
                      <td class="px-3 py-2">
                        <span class="bg-indigo-100 text-indigo-700 text-xs font-medium px-2 py-0.5 rounded">{{ p.patent_id }}</span>
                      </td>
                      <td class="px-3 py-2 text-right font-bold text-indigo-700">{{ p.num_focal_terms }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
                <h2 class="text-sm font-semibold text-slate-600 mb-4">Most frequently shared terms (top 20)</h2>
                <div class="h-72">
                  <ChartWidget type="bar" :data="mostUsedChart" :options="horizBarOpts" />
                </div>
              </div>
            </section>
          </template>
        </template>
      </template>

      <!-- ─────────────────────────────────────────────────────
           TAB: Step 1 — Focal Terms
           Powered by 01_focal_terms_full.json
      ──────────────────────────────────────────────────────── -->
      <template v-else-if="activeTab === 'step1'">
        <section class="bg-indigo-50 border border-indigo-100 rounded-xl p-5">
          <h2 class="font-semibold text-indigo-800 mb-2">What Step 1 does</h2>
          <p class="text-sm text-slate-700 leading-relaxed mb-3">
            A <em>focal term</em> is any term that appears in <strong>both</strong> a patent and at least one of its cited scientific papers.
            The identification pipeline has four stages:
          </p>
          <ol class="list-decimal list-inside space-y-2 text-sm text-slate-700 leading-relaxed">
            <li>
              <strong>Load patent terms</strong> from <code class="bg-white px-1 rounded text-xs border">FullSampleGloria_Pat_GlinerLabels.parquet</code>.
              Group by <code class="bg-white px-1 rounded text-xs border">(patent_id, term)</code> and count occurrences →
              column <code class="bg-white px-1 rounded text-xs border">freq_in_patent</code>.
            </li>
            <li>
              <strong>Clean the link table</strong> from <code class="bg-white px-1 rounded text-xs border">FullSampleGloria_Link_PmidOa.parquet</code>.
              Drop rows without a PMID and remove duplicate
              <code class="bg-white px-1 rounded text-xs border">(patent_id, pmid)</code> pairs → clean patent–paper link table.
            </li>
            <li>
              <strong>Load paper terms</strong> from <code class="bg-white px-1 rounded text-xs border">FullSampleGloria_Pmed_GlinerLabels.parquet</code>.
              Merge with the cleaned link table to attach <code class="bg-white px-1 rounded text-xs border">patent_id</code> to each paper term.
              Group by <code class="bg-white px-1 rounded text-xs border">(patent_id, term)</code> →
              column <code class="bg-white px-1 rounded text-xs border">freq_in_cited_paper</code>.
            </li>
            <li>
              <strong>Inner-join</strong> patent terms and cited-paper terms on
              <code class="bg-white px-1 rounded text-xs border">(patent_id, term)</code>.
              Any term present in both is a focal term.
            </li>
          </ol>
          <p class="text-xs text-slate-500 mt-3">
            📄 Output: <code class="bg-white px-1 rounded border">outcomes/01_focal_terms_full.parquet</code>
            — columns: <code class="bg-white px-1 rounded border">patent_id</code>,
            <code class="bg-white px-1 rounded border">focal_term</code>,
            <code class="bg-white px-1 rounded border">freq_in_patent</code>,
            <code class="bg-white px-1 rounded border">freq_in_cited_paper</code>
          </p>
        </section>

        <div v-if="loadingStep1" class="text-center py-16 text-slate-400 text-sm">Loading step 1 data…</div>
        <div v-else-if="errorStep1" class="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm"> ⚠️ {{ errorStep1 }} </div>
        <template v-else-if="step1">
          <section class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Total (patent, paper, term) triples" :value="fmt(step1.n_rows)" accent="indigo" />
            <StatCard label="Patents covered" :value="fmt(step1.n_patents)" accent="indigo" />
            <StatCard label="PubMed papers linked" :value="fmt(step1.n_pmids)" accent="indigo" />
            <StatCard label="Unique focal terms" :value="fmt(step1.n_focal_terms)" accent="indigo" />
          </section>

          <section class="bg-white rounded-xl shadow-sm border border-slate-200 p-5 text-sm text-slate-600">
            <h2 class="font-semibold text-slate-700 mb-3">Key observations</h2>
            <ul class="list-disc list-inside space-y-1">
              <li>
                On average, each patent has about
                <strong>{{ (step1.n_rows / step1.n_patents).toFixed(1) }}</strong>
                focal-term occurrences (total triples ÷ patents).
              </li>
              <li>
                The dataset covers <strong>{{ fmt(step1.n_pmids) }}</strong> unique PubMed papers linked to <strong>{{ fmt(step1.n_patents) }}</strong> patents.
              </li>
              <li>
                <strong>{{ fmt(step1.n_focal_terms) }}</strong> distinct terms were found in both patent and paper vocabularies.
              </li>
            </ul>
          </section>
        </template>
      </template>

      <!-- ─────────────────────────────────────────────────────
           TAB: Step 2 — Overlap Analysis
           Powered by 02_analysis_full.json
      ──────────────────────────────────────────────────────── -->
      <template v-else-if="activeTab === 'step2'">
        <section class="bg-emerald-50 border border-emerald-100 rounded-xl p-5">
          <h2 class="font-semibold text-emerald-800 mb-2">What Step 2 does</h2>
          <p class="text-sm text-slate-700 leading-relaxed mb-3">
            Using the focal term pairs from Step 1, this step measures <em>overlap intensity</em> — how many focal terms does each patent share with its cited papers?
          </p>
          <ol class="list-decimal list-inside space-y-2 text-sm text-slate-700 leading-relaxed">
            <li>
              Load <code class="bg-white px-1 rounded text-xs border">01_focal_terms_full.parquet</code> and count
              <strong>unique focal terms per patent</strong> via
              <code class="bg-white px-1 rounded text-xs border">groupby("patent_id")["focal_term"].nunique()</code>.
            </li>
            <li>
              Compute <strong>summary statistics</strong> (mean, median, standard deviation, min, max) over the per-patent counts.
            </li>
            <li>
              Visualise the distribution with a <strong>histogram</strong> and a <strong>KDE density plot</strong>, marking mean and median.
            </li>
            <li>
              Identify the <strong>top patents</strong> by focal-term count and rank <strong>terms by frequency</strong> across all patents.
            </li>
          </ol>
          <p class="text-xs text-slate-500 mt-3">
            📄 Output: <code class="bg-white px-1 rounded border">02_focal_term_counts_full.parquet</code>,
            <code class="bg-white px-1 rounded border">02_term_frequency_full.parquet</code>,
            <code class="bg-white px-1 rounded border">02_analysis_full.json</code>
          </p>
        </section>

        <div v-if="loadingStep2" class="text-center py-16 text-slate-400 text-sm">Loading step 2 data…</div>
        <div v-else-if="errorStep2" class="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm"> ⚠️ {{ errorStep2 }} </div>
        <template v-else-if="step2">
          <!-- Summary stats -->
          <section class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Mean terms / patent" :value="step2.summary_stats.mean.toFixed(2)" accent="emerald" />
            <StatCard label="Median" :value="step2.summary_stats.median" accent="emerald" />
            <StatCard label="Max (most overlapping patent)" :value="step2.summary_stats.max" accent="emerald" />
            <StatCard label="Patents with only 1 term" :value="`${step2.summary_stats.pct_exactly_1.toFixed(1)}%`" accent="emerald" />
          </section>

          <!-- Table + chart side by side -->
          <section class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <!-- Top 10 patents -->
            <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
              <h2 class="text-sm font-semibold text-slate-600 mb-4">Top 10 patents by focal-term count</h2>
              <table class="w-full text-sm">
                <thead class="bg-slate-50">
                  <tr>
                    <th class="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">#</th>
                    <th class="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Patent ID</th>
                    <th class="px-3 py-2 text-right text-xs font-semibold text-slate-500 uppercase">Focal terms</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(p, i) in step2.top_10_patents" :key="p.patent_id" class="border-t border-slate-100 hover:bg-emerald-50 transition-colors">
                    <td class="px-3 py-2 text-slate-400">{{ i + 1 }}</td>
                    <td class="px-3 py-2">
                      <span class="bg-emerald-100 text-emerald-700 text-xs font-medium px-2 py-0.5 rounded">
                        {{ p.patent_id }}
                      </span>
                    </td>
                    <td class="px-3 py-2 text-right font-bold text-emerald-700">{{ p.num_focal_terms }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Most used terms chart -->
            <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
              <h2 class="text-sm font-semibold text-slate-600 mb-4">Most frequently shared terms (top 20)</h2>
              <div class="h-72">
                <ChartWidget type="bar" :data="mostUsedChart" :options="horizBarOpts" />
              </div>
            </div>
          </section>

          <!-- Rarest terms -->
          <section class="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
            <h2 class="text-sm font-semibold text-slate-600 mb-3">
              Rarest focal terms
              <span class="text-xs font-normal text-slate-400 ml-1">(appear only once across all patent-paper pairs)</span>
            </h2>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="t in step2.least_used_terms"
                :key="t.focal_term"
                class="bg-slate-100 text-slate-600 text-xs px-2.5 py-1 rounded-full hover:bg-slate-200 transition-colors"
                >{{ t.focal_term }}</span
              >
            </div>
          </section>

          <!-- Searchable, paginated terms browser -->
          <section class="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
            <h2 class="text-sm font-semibold text-slate-600 mb-3">Browse all focal terms</h2>
            <div class="flex flex-col sm:flex-row gap-3 mb-4">
              <input
                v-model="termSearch"
                type="text"
                placeholder="Search terms…"
                class="flex-1 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
              />
              <span class="text-xs text-slate-400 self-center whitespace-nowrap">
                {{ filteredTerms.length }} result{{ filteredTerms.length !== 1 ? 's' : '' }}
              </span>
            </div>
            <table class="w-full text-sm">
              <thead class="bg-slate-50">
                <tr>
                  <th class="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Term</th>
                  <th class="px-3 py-2 text-right text-xs font-semibold text-slate-500 uppercase">Frequency</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="t in pagedTerms"
                  :key="t.focal_term"
                  class="border-t border-slate-100 hover:bg-indigo-50 transition-colors"
                >
                  <td class="px-3 py-2 font-medium text-slate-700">{{ t.focal_term }}</td>
                  <td class="px-3 py-2 text-right text-indigo-700 font-semibold">{{ t.frequency }}</td>
                </tr>
              </tbody>
            </table>
            <div class="flex items-center justify-between mt-4">
              <button
                :disabled="termPage <= 1"
                @click="termPage--"
                class="text-xs px-3 py-1.5 rounded-lg border border-slate-200 disabled:opacity-40 hover:bg-slate-50 transition-colors"
              >← Previous</button>
              <span class="text-xs text-slate-500">Page {{ termPage }} / {{ totalTermPages }}</span>
              <button
                :disabled="termPage >= totalTermPages"
                @click="termPage++"
                class="text-xs px-3 py-1.5 rounded-lg border border-slate-200 disabled:opacity-40 hover:bg-slate-50 transition-colors"
              >Next →</button>
            </div>
          </section>
        </template>
      </template>

      <!-- ─────────────────────────────────────────────────────
           TAB: Step 3 — Semantic Context
           Powered by viewer_data_full.json (similarity section)
      ──────────────────────────────────────────────────────── -->
      <template v-else-if="activeTab === 'step3'">
        <section class="bg-purple-50 border border-purple-100 rounded-xl p-5">
          <h2 class="font-semibold text-purple-800 mb-2">What Step 3 does</h2>
          <p class="text-sm text-slate-700 leading-relaxed mb-3">
            For a sample of 20,000 focal pairs, this step asks:
            <em>"Is this term used in the same way in the patent as in the cited scientific paper?"</em>
            The approach is <strong>co-occurring term analysis + sentence embedding similarity</strong>.
          </p>
          <ol class="list-decimal list-inside space-y-2 text-sm text-slate-700 leading-relaxed">
            <li>
              <strong>Map focal terms to PMIDs.</strong> For each <code class="bg-white px-1 rounded text-xs border">(patent_id, focal_term)</code>,
              find the cited PMIDs that <em>actually contain</em> the focal term — restricting the paper context to papers that genuinely use the term.
            </li>
            <li>
              <strong>Build contexts.</strong>
              <em>Patent context</em>: all other terms in the patent (the focal term itself excluded).
              <em>Paper context</em>: union of all terms across the relevant cited PMIDs (focal term excluded).
            </li>
            <li>
              <strong>Serialise to sentences.</strong> Each context becomes
              <code class="bg-white px-1 rounded text-xs border">"&lt;focal_term&gt; &lt;term_1&gt; &lt;term_2&gt; ..."</code>.
              The focal term is prepended to anchor the embedding.
            </li>
            <li>
              <strong>Generate embeddings</strong> using
              <code class="bg-white px-1 rounded text-xs border">sentence-transformers/all-MiniLM-L6-v2</code>
              → vectors of shape <code class="bg-white px-1 rounded text-xs border">(n_pairs, 384)</code>.
            </li>
            <li>
              <strong>Compute cosine similarity</strong> row-wise (patent embedding vs. paper embedding).
              A score near <strong>1</strong> means the term is used in a nearly identical context;
              near <strong>0</strong> or negative means very different usage.
            </li>
          </ol>
          <p class="text-xs text-slate-500 mt-3">
            📄 Output: <code class="bg-white px-1 rounded border">03_contexts_full.parquet</code>,
            <code class="bg-white px-1 rounded border">03_similarity_full.parquet</code>,
            <code class="bg-white px-1 rounded border">03_semantic_summary_full.json</code>,
            <code class="bg-white px-1 rounded border">viewer_data_full.json</code>
          </p>
        </section>

        <div v-if="loadingViewer" class="text-center py-16 text-slate-400 text-sm">Loading semantic data…</div>
        <div v-else-if="errorViewer && !viewer" class="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm"> ⚠️ {{ errorViewer }} </div>
        <template v-else-if="viewer?.similarity">
          <!-- Stats grid -->
          <section class="grid grid-cols-2 md:grid-cols-3 gap-4">
            <StatCard label="Mean cosine similarity" :value="viewer.similarity.mean.toFixed(3)" accent="purple" />
            <StatCard label="Median" :value="viewer.similarity.median.toFixed(3)" accent="purple" />
            <StatCard label="Std deviation" :value="viewer.similarity.std.toFixed(3)" accent="purple" />
            <StatCard label="Min (most divergent)" :value="viewer.similarity.min.toFixed(3)" accent="purple" />
            <StatCard label="Max (most similar)" :value="viewer.similarity.max.toFixed(3)" accent="purple" />
            <StatCard label="Pairs evaluated" :value="fmt(viewer.similarity.n_pairs)" accent="purple" />
          </section>

          <!-- Interpretation note -->
          <div class="bg-purple-50 border border-purple-100 rounded-xl px-5 py-4 text-sm text-slate-700">
            <strong class="text-purple-800">Interpretation:</strong> A mean similarity of <strong>{{ viewer.similarity.mean.toFixed(3) }}</strong> suggests
            that, on average, focal terms are used in moderately similar contexts across patents and papers. The spread (std =
            {{ viewer.similarity.std.toFixed(3) }}) indicates significant variation — some terms transfer directly, others are used very differently.
          </div>

          <!-- High / Low examples -->
          <section class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
              <h2 class="text-sm font-semibold text-slate-600 mb-4">
                🔥 Highest similarity
                <span class="text-xs font-normal text-slate-400 ml-1">(term used nearly identically)</span>
              </h2>
              <table class="w-full text-sm">
                <thead class="bg-slate-50">
                  <tr>
                    <th class="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Patent</th>
                    <th class="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Term</th>
                    <th class="px-3 py-2 text-right text-xs font-semibold text-slate-500 uppercase">Score</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="ex in viewer.similarity.high_examples"
                    :key="ex.patent_id + ex.focal_term"
                    class="border-t border-slate-100 hover:bg-purple-50 transition-colors"
                  >
                    <td class="px-3 py-2">
                      <span class="bg-purple-100 text-purple-700 text-xs font-medium px-2 py-0.5 rounded">
                        {{ ex.patent_id }}
                      </span>
                    </td>
                    <td class="px-3 py-2 text-slate-700">{{ ex.focal_term }}</td>
                    <td class="px-3 py-2 text-right font-bold text-green-600">
                      {{ ex.cosine_similarity.toFixed(3) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
              <h2 class="text-sm font-semibold text-slate-600 mb-4">
                ❄️ Lowest similarity
                <span class="text-xs font-normal text-slate-400 ml-1">(very different usage context)</span>
              </h2>
              <table class="w-full text-sm">
                <thead class="bg-slate-50">
                  <tr>
                    <th class="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Patent</th>
                    <th class="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Term</th>
                    <th class="px-3 py-2 text-right text-xs font-semibold text-slate-500 uppercase">Score</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="ex in viewer.similarity.low_examples"
                    :key="ex.patent_id + ex.focal_term"
                    class="border-t border-slate-100 hover:bg-purple-50 transition-colors"
                  >
                    <td class="px-3 py-2">
                      <span class="bg-purple-100 text-purple-700 text-xs font-medium px-2 py-0.5 rounded">
                        {{ ex.patent_id }}
                      </span>
                    </td>
                    <td class="px-3 py-2 text-slate-700">{{ ex.focal_term }}</td>
                    <td class="px-3 py-2 text-right font-bold text-red-500">
                      {{ ex.cosine_similarity.toFixed(3) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </template>
      </template>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import ChartWidget from "./components/ChartWidget.vue";
import StatCard from "./components/StatCard.vue";

const BASE = "https://pub-a827588c5750434081f6c006f6ff6697.r2.dev/outcomes";

const tabs = [
  { id: "overview", label: "Overview" },
  { id: "step1", label: "Step 1 — Focal Terms" },
  { id: "step2", label: "Step 2 — Overlap Analysis" },
  { id: "step3", label: "Step 3 — Semantic Context" },
];
const activeTab = ref("overview");

// ── Data stores ──────────────────────────────────────────────
const viewer = ref(null);
const loadingViewer = ref(true);
const errorViewer = ref("");
const step1 = ref(null);
const loadingStep1 = ref(true);
const errorStep1 = ref("");
const step2 = ref(null);
const loadingStep2 = ref(true);
const errorStep2 = ref("");

async function fetchJSON(url, dataRef, loadingRef, errorRef) {
  loadingRef.value = true;
  errorRef.value = "";
  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`HTTP ${r.status} — ${r.statusText}`);
    dataRef.value = await r.json();
  } catch (e) {
    errorRef.value = e.message;
  } finally {
    loadingRef.value = false;
  }
}

onMounted(() => {
  fetchJSON(`${BASE}/viewer_data_full.json`, viewer, loadingViewer, errorViewer);
  fetchJSON(`${BASE}/01_focal_terms_full.json`, step1, loadingStep1, errorStep1);
  fetchJSON(`${BASE}/02_analysis_full.json`, step2, loadingStep2, errorStep2);
});

// ── Helpers ──────────────────────────────────────────────────
function fmt(n) {
  return Number(n).toLocaleString();
}

// ── Chart configs ─────────────────────────────────────────────
const INDIGO = "rgba(99,102,241,0.75)";
const EMERALD = "rgba(16,185,129,0.65)";
const EMERALD2 = "rgba(16,185,129,0.75)";

const topTermsChart = computed(() => ({
  labels: viewer.value?.top_terms.map((t) => t.focal_term) ?? [],
  datasets: [
    {
      label: "Patents",
      data: viewer.value?.top_terms.map((t) => t.patent_count) ?? [],
      backgroundColor: INDIGO,
      borderRadius: 4,
    },
  ],
}));

const distChart = computed(() => ({
  labels: viewer.value?.distribution.map((b) => b.bin) ?? [],
  datasets: [
    {
      label: "Patents",
      data: viewer.value?.distribution.map((b) => b.count) ?? [],
      backgroundColor: EMERALD,
      borderRadius: 4,
    },
  ],
}));

const mostUsedChart = computed(() => ({
  labels: step2.value?.most_used_terms.map((t) => t.focal_term) ?? [],
  datasets: [
    {
      label: "Frequency",
      data: step2.value?.most_used_terms.map((t) => t.frequency) ?? [],
      backgroundColor: EMERALD2,
      borderRadius: 4,
    },
  ],
}));

const horizBarOpts = {
  indexAxis: "y",
  plugins: { legend: { display: false } },
  scales: { x: { beginAtZero: true } },
};

const distOpts = {
  plugins: { legend: { display: false } },
  scales: {
    x: { title: { display: true, text: "Focal terms per patent" } },
    y: { beginAtZero: true },
  },
};

// ── Semantic summary cards ────────────────────────────────────
const simCards = computed(() => {
  const s = viewer.value?.similarity;
  if (!s) return [];
  return [
    { label: "Mean", value: s.mean.toFixed(3) },
    { label: "Median", value: s.median.toFixed(3) },
    { label: "Std dev", value: s.std.toFixed(3) },
    { label: "Min", value: s.min.toFixed(3) },
    { label: "Max", value: s.max.toFixed(3) },
    { label: "Sample pairs", value: fmt(s.n_pairs) },
  ];
});

// ── Terms browser (Step 2 + Overview) ────────────────────────
const TERMS_PER_PAGE = 20;
const termSearch = ref("");
const termPage = ref(1);

const filteredTerms = computed(() => {
  if (!step2.value?.most_used_terms) return [];
  const q = termSearch.value.toLowerCase().trim();
  return q
    ? step2.value.most_used_terms.filter((t) => t.focal_term.toLowerCase().includes(q))
    : step2.value.most_used_terms;
});

const totalTermPages = computed(() => Math.max(1, Math.ceil(filteredTerms.value.length / TERMS_PER_PAGE)));

const pagedTerms = computed(() => {
  const start = (termPage.value - 1) * TERMS_PER_PAGE;
  return filteredTerms.value.slice(start, start + TERMS_PER_PAGE);
});

watch(termSearch, () => {
  termPage.value = 1;
});
</script>
