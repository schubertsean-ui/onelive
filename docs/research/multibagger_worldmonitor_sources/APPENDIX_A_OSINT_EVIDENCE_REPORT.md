# Appendix A — OSINT-signals evidence research report (verbatim agent output)

Provenance: single research-agent web fan-out, 2026-07-22, commissioned for
Session Contract #22 (docs/research/MULTIBAGGER_WORLDMONITOR_INTELLIGENCE_v1.md).
Committed VERBATIM per the in-diff evidence rule (PR #47 evaluator r1; PR #18
r6–r7 precedent). The agent's own reliability caveat: every direct page fetch
was blocked by the sandbox egress proxy (CONNECT 403), so every claim is
SEARCH-SNIPPET grade — R-024 gates re-verification.

---

I have comprehensive coverage. Note: WebFetch to external hosts was blocked by the organization's egress proxy (403 CONNECT denials for gnu.org, fsf.org, wikipedia.org, opensource.com, arxiv.org, etc.), so no source could be full-text fetched. Every citation below is therefore labeled SEARCH-SNIPPET (drawn from search-engine result snippets, not verified against fetched page text). Dates are given where identifiable from the source; where a snippet did not expose a date I mark it "date n/d."

# OSINT Signals for Long-Horizon Fundamental Equity Selection — Evidence Report

Scope caveat on verification: All items are SEARCH-SNIPPET. Full-text fetch was unavailable this session (proxy policy denial). Snippet paraphrases can compress or distort authors' claims; treat quantitative figures as indicative pending direct reading of the linked papers.

## 1. GDELT and market prediction

Positive/mixed findings (SEARCH-SNIPPET)
- BBVA Research working paper 22/05, "Measuring news media sentiment using big data for Chinese stock markets" (published ScienceDirect, Pacific-Basin Finance Journal, 2022): GDELT-constructed sentiment shows "significant predictive power for stock market returns and volatilities"; sentiment-extended EGARCH improves return/volatility forecast accuracy. URL: https://www.bbvaresearch.com/wp-content/uploads/2022/07/News-Media-Sentiments-from-Big-Data-with-author-info.pdf ; https://www.sciencedirect.com/science/article/abs/pii/S0927538X22001056 (date: 2022). SEARCH-SNIPPET.
- Utrecht/Twente thesis (Jakel, essay.utwente.nl/78614, date n/d): cross-correlation of GDELT average sentiment vs closing price is asset-dependent — Alphabet strong same-day positive; Facebook and Tesla weak negative — i.e., no stable cross-asset signal. URL: https://essay.utwente.nl/78614/1/Final%20Thesis%20Tibor%20Jakel%201850067.pdf . SEARCH-SNIPPET.
- arXiv 2505.16136 "Interpretable Machine Learning for Macro Alpha: A News Sentiment Case Study" (2025): builds on GDELT + FinBERT + XGBoost, framed around reproducibility. URL: https://arxiv.org/html/2505.16136v1 (date: 2025). SEARCH-SNIPPET.
- Commodity/oil: study using WTI daily price vs predictors from Twitter, Google Trends, Wikipedia and GDELT with ARIMAX (arXiv 2105.09154; also Journal of Information Science 2017): "GDELT number of articles" among highest-predictive-power variables; platforms compared on days-ahead lead. URL: https://arxiv.org/pdf/2105.09154 ; https://dl.acm.org/doi/abs/10.1177/0165551517698298 (date: 2017/2021). SEARCH-SNIPPET.

Data-quality / reliability critiques (SEARCH-SNIPPET)
- MDPI Data 2025, 10(10):158 "Research on the Development and Application of the GDELT Event Database": accuracy rate of key fields "only approximately 55%," data redundancy "as high as 20%," automated coding introduces duplication and misclassification; recommends deduplication/correction before use. URL: https://www.mdpi.com/2306-5729/10/10/158 (date: 2025). SEARCH-SNIPPET.
- Source/OpenNews "GDELT and the Problem of Decontextualized Data" (author/date n/d; fetch blocked): critique of decontextualization and geocoding/miscoding. URL: https://source.opennews.org/articles/gdelt-decontextualized-data/ . SEARCH-SNIPPET (could not fetch).
- Political Violence at a Glance, "Raining on the Parade: Some Cautions Regarding GDELT" (2014-02-20): early caution on inferential use of GDELT events. URL: https://politicalviolenceataglance.org/2014/02/20/raining-on-the-parade-some-cautions-regarding-the-global-database-of-events-language-and-tone-dataset/ (date: 2014-02-20). SEARCH-SNIPPET.
- Western/English-language and gatekeeping bias; unreliable in censored regions; geolocation in data-poor environments "no more certain than a coin toss" — recurring across AIB Insights (insights.aib.world/article/66442), City U. London "Lifting the Veil on the Use of Big Data News Repositories" (openaccess.city.ac.uk/id/eprint/28866), and SBP-BRiMS 2025 working paper 12. URLs: https://insights.aib.world/article/66442 ; https://openaccess.city.ac.uk/id/eprint/28866/1/ ; https://sbp-brims.org/2025/papers/working-papers/2025_SBP-BRiMS_paper_12.pdf . SEARCH-SNIPPET.

Net: GDELT-based equity prediction results are asset-, method-, and period-specific (no robust general result surfaced in snippets); documented structural data-quality problems (~55% field accuracy, ~20% redundancy, coverage bias, geocoding error) are the main critique. No single canonical "replication failure" paper surfaced; caution/critique literature dominates.

## 2. News-analytics alpha (RavenPack / Bloomberg) and decay

Vendor/practitioner evidence (SEARCH-SNIPPET, RavenPack-published — source-of-interest bias)
- RavenPack "News Sentiment Everywhere – Trading Global Equities" (Data Science Team; ResearchGate 351360244): documents cross-market equity sentiment strategies. URL: https://www.ravenpack.com/research/news-sentiment-everywhere/ ; https://www.researchgate.net/publication/351360244 (date n/d). SEARCH-SNIPPET.
- Decay pattern (RavenPack research snippets): "information ratio decay in the signal is fast"; positive events decay over ~2 days, negative over ~5 days; on a cumulative-returns basis signals "continued to be successful for up to a month ahead"; decay slower for small-cap than large/mid-cap (lower liquidity, slower news incorporation). URL: https://www.ravenpack.com/research/ (date n/d). SEARCH-SNIPPET.
- "Attention Conditions Stock Market Reaction to News Sentiment": reaction magnitude conditioned on investor attention. URL: https://www.ravenpack.com/research/stock-market-reaction-to-news-sentiment/ . SEARCH-SNIPPET.
- MSCI/Barra: uses RavenPack News Sentiment to enhance the short-term-trading Barra risk model; news-sentiment factors "effective in explaining the cross-section of stock returns" (short-term). SEARCH-SNIPPET.

Horizon question (SEARCH-SNIPPET)
- Academic/quant snippets are mixed on whether news-sentiment alpha survives past intraday: one line "significant news events can be absorbed on intraday timescales" (daily models capture residual drift); another (arXiv 2509.11970 / MDPI 2673-2688) reports a long-short sentiment strategy earning "economically meaningful returns across all horizons, strongest at 3 months," profitable after moderate transaction costs but with Sharpe declining as costs rise. URLs: https://arxiv.org/pdf/2509.11970 ; https://www.mdpi.com/2673-2688/7/4/138 (date: 2025/2026). SEARCH-SNIPPET.
- ar5iv 1807.06824 "News-based trading strategies": profitability contingent on frictions. URL: https://ar5iv.labs.arxiv.org/html/1807.06824 (date: 2018). SEARCH-SNIPPET.

Net: Documented news-sentiment edge is strongest intraday-to-days; some evidence of returns persisting to weeks–3 months (stronger in small-caps, slower diffusion). Fast information-ratio decay and transaction-cost sensitivity are the consistent caveats. Most quantitative decay figures come from the vendor (RavenPack) itself.

## 3. Event/catalyst timing and shock propagation

Post-earnings-announcement drift (PEAD) (SEARCH-SNIPPET)
- "A review of the Post-Earnings-Announcement Drift" (ScienceDirect S2214635020303750): PEAD "one of the most solidly documented asset pricing anomalies." URL: https://www.sciencedirect.com/science/article/pii/S2214635020303750 . SEARCH-SNIPPET.
- Persistence debate: weakening reported by Richardson et al. 2010, Chordia-Subrahmanyam-Tong 2014, Martineau 2022; contested by others finding strong PEAD 2008–2019 using text-based surprise definitions. SSRN 4751735 (Fang) finds PEAD persisted through COVID-19 and is stronger with broader disclosure of systemic shocks. URLs: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4751735 ; https://jkatz.caltech.edu/documents/28622/peads.pdf . SEARCH-SNIPPET.
- JFQA (Cambridge, 2024) experimental evidence: prices underadjust to fundamental-value changes; strategies can exploit PEAD. URL: https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/61CD6A2065A4686418A3C47DEF3AC24B (date: 2024). SEARCH-SNIPPET.

Supplier-shock / production-network propagation (SEARCH-SNIPPET)
- Barrot & Sauvagnat, "Input Specificity and the Propagation of Idiosyncratic Shocks in Production Networks," QJE 131(3):1543–1592, Aug 2016: natural-disaster shocks to suppliers cut supplier sales growth ~5 pp and customer sales growth ~2 pp; "significant market value losses that spill over to other suppliers"; horizontal propagation to other suppliers of affected customers; effect concentrated in specific (hard-to-substitute) inputs. URL: https://academic.oup.com/qje/article-abstract/131/3/1543/2461213 ; https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2427421 (date: 2016). SEARCH-SNIPPET.
- Related newer work: arXiv 2606.29290 "Supply Chain Propagation of Textual Signals: LLM Embeddings and Cross-Sectional Return Predictability" (cross-sectional return predictability along supply chains). URL: https://arxiv.org/pdf/2606.29290 (date: 2026). SEARCH-SNIPPET.

Supply-chain disruption equity impact (SEARCH-SNIPPET)
- Classic result cited in snippets: supply-chain "glitch" announcements → average firm value loss ~10.28% over 2 days (Hendricks-Singhal lineage). SEARCH-SNIPPET.
- Suez / "Ever Given" blockage: ScienceDirect S0925527324003219 "The costs of maritime supply chain disruptions: the case of the Suez Canal blockage" — ~$9.6B/day trade delayed, Asia-Europe freight spike for months. URL: https://www.sciencedirect.com/science/article/abs/pii/S0925527324003219 . SEARCH-SNIPPET.
- Shanghai 2022 lockdown: Wiley, Asia-Pacific J. Financial Studies (Song, 2025) "Stock Market Reactions to Supply Chain Disruptions and Recovery from the 2022 Shanghai Lockdown." URL: https://onlinelibrary.wiley.com/doi/full/10.1111/ajfs.70003 (date: 2025). SEARCH-SNIPPET.
- Sectoral: Nature Humanities & Social Sciences Communications (2025) "The impact of global supply chain pressure on the stock market: A sectoral view" — depresses industrial-sector returns via cost/production channels. URL: https://www.nature.com/articles/s41599-025-04634-0 (date: 2025). SEARCH-SNIPPET.
- Chip shortage differential: semis (Intel, TSMC) gained; automakers (Ford) fell on production delays; ~$210B auto-industry cost 2021; 94% of Fortune 1000 hit by COVID supply shocks. SEARCH-SNIPPET.

Sanctions / regulatory-action drift (SEARCH-SNIPPET)
- Russian equities event study (RJMF 2020): sanctions announcements produce statistically significant negative abnormal returns accumulating over subsequent days; firm-specific study of 8 sanctions / 14 entities → statistically significant −5.4% CAR over 7-day window. URL: https://rjmf.econs.online/en/2020/1/sanctions-and-the-russian-equity-market/ (date: 2020). SEARCH-SNIPPET.
- Entity-List supply-chain ripple (ABFER 2025, "Export Restrictions and the Ripple Effect: US-China Trade Networks"): US suppliers of sanctioned Chinese firms −2.93% 3-factor CAR; Chinese upstream suppliers +3.48% (substitution expectation). URL: https://abfer.org/media/abfer-events-2025/posters/selected-papers/PS25065_Export-Restrictions-and-the-Ripple-Effect_Evidence-from-US-China-Trade-Networks.pdf (date: 2025). SEARCH-SNIPPET.
- Russia-Ukraine financial sanctions: Finance Research Letters (ScienceDirect S1544612323007705) — global reaction stronger for politically-connected firms, weaker where geopolitical risk higher. URL: https://www.sciencedirect.com/science/article/abs/pii/S1544612323007705 (date: 2023). SEARCH-SNIPPET.
- SEC investigations/enforcement: investigation-announcement window CAR ≈ −6% (larger than sanction window); enforcement actions ≈ −1% to −2% over 5 surrounding days; more negative where prior-year earnings management larger; smaller effect for large caps. Sources: tandfonline 10.1080/21697221.2014.891069; ScienceDirect 0278425494900035; Harvard PCG Tribukait paper. URLs: https://www.tandfonline.com/doi/full/10.1080/21697221.2014.891069 ; https://www.sciencedirect.com/science/article/abs/pii/0278425494900035 ; https://pcg.law.harvard.edu/wp-content/uploads/papers/Tribukait_Paper.pdf . SEARCH-SNIPPET.

Net: Post-event drift (PEAD, sanctions, investigations) is repeatedly documented with measurable magnitudes and multi-day-to-weeks windows — i.e., catalyst-timing evidence exists. Supplier-network propagation (Barrot-Sauvagnat) gives a quantified basis for "adjacent/indirect" exposure mapping.

## 4. Country / political-risk measures and asset prices

(SEARCH-SNIPPET)
- Hassan, Hollander, van Lent, Tahoun, "Firm-Level Political Risk: Measurement and Effects," QJE 134(4):2135–2202, 2019 (NBER WP 24029, 2017): text-based PRisk from earnings-call transcripts; validated as correlating with firm-level stock-return volatility; politically exposed firms retrench hiring/investment and increase lobbying/donations; eight topic sub-measures (economic policy & budget, environment, trade, institutions, health, security & defense, tax, tech/infrastructure). Data public at policyuncertainty.com/firm_pr.html. URLs: https://www.nber.org/papers/w24029 ; https://academic.oup.com/qje/advance-article/doi/10.1093/qje/qjz021/5531768 ; https://www.policyuncertainty.com/firm_pr.html (date: 2019). SEARCH-SNIPPET. Note: snippets document association with volatility and firm actions; they do not, in what was retrieved, establish that PRisk changes predict the cross-section of returns — that specific directional-return claim is not confirmed here.
- Country-instability modeling: arXiv 2411.06639 "Predicting Country Instability Using Bayesian Deep Learning and Random Forest" (2024) — instability prediction from event data. URL: https://arxiv.org/pdf/2411.06639 (date: 2024). SEARCH-SNIPPET.
- No EIU/PRS ICRG-vs-returns predictive study surfaced in the searches run; that sub-question is uncovered by current evidence.

## 5. Prediction markets (Polymarket / Kalshi) as probability inputs

Calibration/accuracy (SEARCH-SNIPPET)
- Bürgi, Deng & Whelan, "Makers and Takers: The Economics of the Kalshi Prediction Market" (CEPR DP20631; UCD WP2025_19; SSRN 5502658), 2025: transaction-level data on 300,000+ contracts; Brier scores + calibration curves; prices "informative and improve in accuracy as markets approach closing" but show a clear favorite–longshot bias (low-price contracts win less than break-even; high-price win more, small positive returns); some weakening of the bias in 2025 data. URLs: https://cepr.org/publications/dp20631 ; https://www.ucd.ie/economics/t4media/WP2025_19.pdf ; https://www.karlwhelan.com/Papers/Kalshi.pdf (date: 2025). SEARCH-SNIPPET.
- 2024 election accuracy comparisons (secondary/blog sources — lower authority): PredictIt ~93% markets "better than chance," Kalshi ~78%, Polymarket ~67% in one tally; both Kalshi and Polymarket called the presidential winner with higher final-days confidence than most poll aggregates. DL News reports an academic caution that reliability claims are overstated. URLs: https://ahasignals.com/research/election-prediction-market-accuracy-2024/ ; https://www.dlnews.com/articles/markets/polymarket-kalshi-prediction-markets-not-so-reliable-says-study/ (date: 2024/2025). SEARCH-SNIPPET (non-peer-reviewed).
- Market share/liquidity context: Kalshi + Polymarket ≈ 97.5% of prediction-market volume in 2025 (~$238B and ~$220B). URL: https://www.kucoin.com/news/flash/ (truncated in snippet) (date: 2025). SEARCH-SNIPPET.

Equity-catalyst use (SEARCH-SNIPPET)
- Kalshi "Biopharma's Public Probability" (with AppliedXL): contracts on single clinical/regulatory questions (e.g., Phase 3 endpoint, FDA approval by date) yielding market-implied probabilities distinct from whole-company stock pricing. URLs: https://kalshi.com/biotech ; https://www.appliedxl.com/research/biopharma-public-probability (date n/d). SEARCH-SNIPPET.
- Documented equity behavior around the same catalysts: "PDUFA run-up" (biotech stocks drift up in weeks before PDUFA/binary events); arXiv 2208.07248 "New drugs and stock market: how to predict pharma market reaction to clinical trial announcements." URLs: https://www.biopharmawatch.com/blog/ (truncated in snippet) ; https://arxiv.org/pdf/2208.07248 (date: 2022). SEARCH-SNIPPET. Note: these establish that prediction-market probabilities exist for the same catalysts equities react to; they do not, in retrieved snippets, demonstrate a validated trading edge from using PM prices to time those equities.

Net: Kalshi prices are calibrated-but-biased (favorite–longshot), improving toward settlement; direct evidence that PM prices give an equity-catalyst timing edge is not established in retrieved sources — only that PM contracts and equity catalysts (biotech FDA/PDUFA) map onto the same events.

## 6. Practitioner reality check (alt-data / OSINT for fundamental horizons)

(SEARCH-SNIPPET)
- Backtest overfitting / multiple testing: Bailey & López de Prado, "How 'Backtest Overfitting' in Finance Leads to False Discoveries," Significance (RSS), 18(6):22, 2021 — "most discoveries in empirical finance are false" due to selection bias under multiple testing; "optimal" backtested strategies can be "statistical mirages." López de Prado, "A Data Science Solution to the Multiple-Testing Crisis" (SSRN 3177057). Tools: Deflated Sharpe Ratio (adjusts significance for number of trials, skew, kurtosis) and Combinatorial Purged Cross-Validation (CPCV). URLs: https://academic.oup.com/jrssig/article/18/6/22/7038278 ; https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3177057 ; https://sdm.lbl.gov/oapapers/ssrn-id2507040-bailey.pdf (date: 2014/2018/2021). SEARCH-SNIPPET.
- Alpha decay / crowding: arXiv 2512.11913 "Not All Factors Crowd Equally" (2025) — aggregate alpha decays hyperbolically as more agents discover a signal within a fixed "alpha capacity"; mechanical/unambiguous signals (e.g., momentum) crowd, judgment-based signals (value, multiple interpretations) crowd less. Practitioner snippets: signals lose ~5–10% effectiveness/year in US/EU markets, faster under stress; alt-data signals "erode within months" as competitors adopt the same source. URL: https://arxiv.org/html/2512.11913v1 (date: 2025). SEARCH-SNIPPET.
- Signal-vs-noise in alt-data: "limited sample sizes and irregular timestamps" make separating true signal from false positives hard (general practitioner framing). SEARCH-SNIPPET.
- Point-in-time / bias requirements (CFA/AnalystPrep; LuxAlgo; portfoliooptimizationbook "Seven Sins"): survivorship bias can overstate annual returns by 1–4%; look-ahead bias (using restated/later-available data) yields "excessively optimistic" backtests; remedy is point-in-time data including delisted securities and original (non-restated) fundamentals. URLs: https://analystprep.com/study-notes/cfa-level-2/problems-in-backtesting/ ; https://www.luxalgo.com/blog/survivorship-bias-in-backtesting-explained/ ; https://portfoliooptimizationbook.com/book/8.2-seven-sins.html (date n/d). SEARCH-SNIPPET.

Net: The practitioner literature's consistent messages: (i) most backtested signals are false discoveries absent multiple-testing correction (deflated Sharpe/CPCV); (ii) alt-data alpha crowds and decays within months, faster for mechanical signals; (iii) point-in-time data (delisted names, original vintages) is mandatory to avoid look-ahead/survivorship overstatement of 1–4%+.

## 7. AGPL-3.0 posture for internal self-hosted use

Verification note: The authoritative primary sources (gnu.org GPL FAQ, gnu.org AGPL-3.0 text, fsf.org AGPLv3 bulletin) and secondary explainers (Wikipedia, opensource.com, ospo.co) were all blocked by the egress proxy (403), so none could be full-text-verified this session. The following reflects search-result snippets only.

(SEARCH-SNIPPET)
- AGPLv3 Section 13 network-source obligation is triggered by conveying/offering the software to users interacting with it "remotely through a computer network," and in practice snippets state it is triggered where the AGPL software "has been modified by 'you'" (the service provider): "So long as 'you' do not modify the AGPLv3 code, the license should not be read as requiring access to the Corresponding Source in the manner prescribed by Section 13" (attributed to opensource.com, Van Lindberg, 2017-01). URL (blocked): https://opensource.com/article/17/1/providing-corresponding-source-agplv3-license (date: 2017). SEARCH-SNIPPET.
- "Many unmodified and standard deployments of software modules under AGPL simply do not trigger Section 13." SEARCH-SNIPPET.
- "Purely internal use can occur without imposing any obligations. This is technically true for the AGPL as well." (ospo.co Q&A, date n/d; blocked). URL (blocked): https://ospo.co/blog/questions-and-answers-about-the-agpl/ . SEARCH-SNIPPET.
- Section 13 language (AGPL-3.0 text): if you modify the Program, the modified version "must prominently offer all users interacting with it remotely through a computer network … an opportunity to receive the Corresponding Source." The trigger is (a) modification and (b) making it available to remote users. URL (blocked): https://www.gnu.org/licenses/agpl-3.0.en.html . SEARCH-SNIPPET.
- Compliance guides (SK Telecom OSS guide; Vaultinum; FOSSA; Search-Guard) corroborate that the network-user source offer attaches to modified versions offered to remote (network) users. URLs: https://sktelecom.github.io/en/guide/use/obligation/agpl-3.0/ ; https://vaultinum.com/blog/essential-guide-to-agpl-compliance-for-tech-companies ; https://fossa.com/blog/open-source-software-licenses-101-agpl-license/ . SEARCH-SNIPPET.

Consolidated snippet-level conclusion: Running AGPL-3.0 software where the only network users are members of your own organization (no external/third-party users) — and especially running it unmodified — is reported by these sources as not triggering a Section 13 source-disclosure obligation to third parties. Two independent conditions each point that way in the snippets: (i) no outside users to whom the "offer" would run, and (ii) no modification (Section 13's remote-user offer attaches to a modified version). Caveat: the FSF/GNU FAQ (the single most authoritative statement on "who counts as a user" and the private-modification carve-out that parallels GPLv3) could not be fetched to confirm exact wording; the above rests on secondary/compliance sources and blocked-primary snippets. Recommend direct reading of gnu.org/licenses/gpl-faq.html (entries on AGPL, "internal use," and private/unshared modifications) and AGPL-3.0 §13 before relying on this for a formal legal position.

## Coverage gaps (not established by retrieved evidence)
- No canonical GDELT equity-return replication-failure paper surfaced (only data-quality critiques).
- EIU / PRS-Group ICRG country-risk-vs-returns predictive studies: not retrieved.
- Hassan et al. PRisk: snippets confirm association with volatility and firm actions, not directional cross-sectional return prediction.
- Prediction-market prices → validated equity-catalyst timing edge: not demonstrated (only shared-event mapping).
- Bloomberg (vs RavenPack) news-sentiment performance: not separately documented in searches run.
- All AGPL primary sources unverified due to proxy block; secondary sources agree but exact FSF FAQ wording on "internal users" and the private-modification carve-out remains unconfirmed this session.
