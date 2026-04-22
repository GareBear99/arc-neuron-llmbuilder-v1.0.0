#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/configs/production/real_gguf_build.env"
[[ -f "$ENV_FILE" ]] || { echo "Missing ${ENV_FILE}. Copy the example and edit it." >&2; exit 2; }
"$ROOT_DIR/scripts/production/validate_real_gguf_build.sh" "$ENV_FILE"
source "$ENV_FILE"
REPORT_DIR="$ROOT_DIR/reports/real_gguf_build"
mkdir -p "$REPORT_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="$REPORT_DIR/${COGNITION_CANDIDATE_ID}_$STAMP"
mkdir -p "$RUN_DIR"
export RUN_DIR FLAGSHIP_MODEL_NAME FLAGSHIP_VERSION MODEL_FAMILY PROMPT_PROFILE MAX_CONTEXT_TOKENS BUILD_LLAMAFILE
export COGNITION_CANDIDATE_ID COGNITION_BASE_MODEL_DIR COGNITION_MERGED_MODEL_DIR COGNITION_FP16_MODEL_FILE COGNITION_QUANTIZED_MODEL_FILE COGNITION_RUNTIME_BINARY COGNITION_QUANT_TYPE
if [[ "${BUILD_LLAMAFILE:-1}" == "1" ]]; then export COGNITION_LLAMAFILE_FILE; fi
if [[ -n "${COGNITION_MERGE_COMMAND:-}" ]]; then bash -lc "$COGNITION_MERGE_COMMAND" | tee "$RUN_DIR/merge.log"; else echo "No COGNITION_MERGE_COMMAND set; assuming merged model already exists" | tee "$RUN_DIR/merge.log"; fi
"$COGNITION_PYTHON_BIN" "$COGNITION_CONVERT_SCRIPT" "$COGNITION_MERGED_MODEL_DIR" --outfile "$COGNITION_FP16_MODEL_FILE" ${COGNITION_CONVERT_EXTRA_ARGS:-} | tee "$RUN_DIR/convert.log"
[[ -s "$COGNITION_FP16_MODEL_FILE" ]] || { echo "FP16 GGUF missing or empty" >&2; exit 6; }
"$COGNITION_QUANTIZE_BIN" "$COGNITION_FP16_MODEL_FILE" "$COGNITION_QUANTIZED_MODEL_FILE" "${COGNITION_QUANT_TYPE:-Q4_K_M}" | tee "$RUN_DIR/quantize.log"
[[ -s "$COGNITION_QUANTIZED_MODEL_FILE" ]] || { echo "Quantized GGUF missing or empty" >&2; exit 7; }
if [[ "${BUILD_LLAMAFILE:-1}" == "1" ]]; then cp "$COGNITION_LLAMAFILE_BINARY" "$COGNITION_LLAMAFILE_FILE" && cat "$COGNITION_QUANTIZED_MODEL_FILE" >> "$COGNITION_LLAMAFILE_FILE" && chmod +x "$COGNITION_LLAMAFILE_FILE"; fi
python3 - <<'PY'
import hashlib, json, os, socket, time
files={'fp16_gguf':os.environ['COGNITION_FP16_MODEL_FILE'],'quantized_gguf':os.environ['COGNITION_QUANTIZED_MODEL_FILE']}
if os.environ.get('BUILD_LLAMAFILE','1') == '1': files['llamafile']=os.environ['COGNITION_LLAMAFILE_FILE']
out={'candidate_id':os.environ['COGNITION_CANDIDATE_ID'],'flagship_model_name':os.environ['FLAGSHIP_MODEL_NAME'],'flagship_version':os.environ['FLAGSHIP_VERSION'],'model_family':os.environ['MODEL_FAMILY'],'prompt_profile':os.environ.get('PROMPT_PROFILE','flagship'),'max_context_tokens':int(os.environ.get('MAX_CONTEXT_TOKENS','8192')),'runtime_binary':os.environ['COGNITION_RUNTIME_BINARY'],'base_model_dir':os.environ['COGNITION_BASE_MODEL_DIR'],'merged_model_dir':os.environ['COGNITION_MERGED_MODEL_DIR'],'quantization':os.environ.get('COGNITION_QUANT_TYPE','Q4_K_M'),'created_at':time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),'build_host':socket.gethostname(),'artifacts':{}}
for name,path in files.items():
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''): h.update(chunk)
    out['artifacts'][name]={'path':path,'sha256':h.hexdigest(),'size_bytes':os.path.getsize(path)}
manifest=os.path.join(os.environ['RUN_DIR'],'real_gguf_manifest.json')
with open(manifest,'w',encoding='utf-8') as fh: json.dump(out, fh, indent=2)
print(manifest)
PY
