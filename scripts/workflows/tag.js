export const meta = {
  name: 'nonprofit-program-dna-tag',
  description: 'Tag youth nonprofit program descriptions (mentoring, bridging, program types, evidence) per protocol, writing validated JSON to disk',
  phases: [{ title: 'Tag', detail: 'one agent per batch of 150 organizations' }],
}
const ROOT = '/home/user/claude_projects/projects/10-nonprofit-program-dna'
const SCHEMA = {
  type: 'object',
  properties: { batch: { type: 'string' }, n_records: { type: 'integer' }, n_mentoring: { type: 'integer' }, valid: { type: 'boolean' }, issues: { type: 'string' } },
  required: ['batch', 'n_records', 'n_mentoring', 'valid', 'issues'],
}
// args: {jobs: [{pass: 'main'|'reference', batch: 'batch_0001', model?: 'sonnet'}]}
const prompt = (j) => `You are tagging nonprofit program descriptions from IRS Form 990 filings for a research map of youth mentoring supply.${j.pass === 'reference' ? '' : ''}
Another tagger codes some batches independently: do NOT open anything under ${ROOT}/data/coded/ except your own output file.

1. Read ${ROOT}/docs/protocol.md and follow it exactly. Tag only what each organization's text states.
2. Read the input batch ${ROOT}/data/interim/batches/org/${j.batch}.jsonl (one JSON record per line: id = EIN, name, ntee, city, state, mission, programs). Read EVERY record's mission and program descriptions IN FULL (print in chunks).
3. For every record produce one object with exactly these keys: id, youth_focus, mentoring, mentoring_types, bridging, program_types, targets, ages, youth_served, dose_stated, outcomes_claimed, evidence_level, notes. "id" is the EIN string. notes: at most 15 words, your own words, NEVER any person's name (filings sometimes name staff or participants; leave them out).
4. Write the JSON list to ${ROOT}/data/coded/${j.pass}/${j.batch}.json (create folders if needed; a short Python script is fine).
5. Run: python3 -I ${ROOT}/scripts/validate.py ${ROOT}/data/coded/${j.pass}/${j.batch}.json and fix until it prints VALID.
6. Keep ALL temporary files in your PRIVATE folder ${ROOT}/data/interim/tmp/${j.pass}_${j.batch}/ (create it). Never use the shared scratchpad or /tmp: other agents run at the same time. Build the output by matching each record's id, never by position. Do not modify any other files. Do not run git.
Return counts from your final file (n_mentoring = records with mentoring central or component); valid=true only if the validator printed VALID. In "issues", confirm you read every record in full and note hard calls briefly.`
// shorthand: args {main: [...batches], reference: [...batches], model: 'sonnet'} -> jobs (reference interleaved, default model)
if (!args.jobs) {
  const jobs = (args.main || []).map(b => ({ pass: 'main', batch: b, model: args.model || 'sonnet' }))
  ;(args.reference || []).forEach((b, k) => jobs.splice(Math.min(jobs.length, 6 + k * 12), 0, { pass: 'reference', batch: b }))
  args.jobs = jobs
}
log(`Tagging ${args.jobs.length} batch(es)`)
const results = await parallel(args.jobs.map(j => () =>
  agent(prompt(j), { label: `${j.pass} ${j.batch}`, phase: 'Tag', schema: SCHEMA, ...(j.model ? { model: j.model } : {}) })))
const ok = results.filter(Boolean)
log(`Done: ${ok.filter(r => r.valid).length}/${args.jobs.length} valid`)
return ok
