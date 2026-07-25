#!/usr/bin/env bash
BASE="http://127.0.0.1:8080"
PASS=0; FAIL=0; ERRORS=""

t() {
  local label="$1" method="$2" url="$3" data="$4"
  local cmd="curl -s -X $method"
  [[ -n "$data" ]] && cmd="$cmd -H 'Content-Type: application/json' -d '$data'"
  cmd="$cmd $BASE$url"
  local resp; resp=$(eval "$cmd" 2>&1)
  local ok; ok=$(echo "$resp" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('ok','ERR'))" 2>/dev/null || echo "PARSE_ERR")
  if [[ "$ok" == "True" || "$ok" == "true" ]]; then
    echo "  PASS  $method $url"
    ((PASS++))
  else
    echo "  FAIL  $method $url  ok=$ok"
    echo "        $(echo "$resp" | head -c 200)"
    ERRORS="$ERRORS\n  $method $url ok=$ok"
    ((FAIL++))
  fi
}

echo "===== Health & Stats ====="
t health GET /api/health
t stats-overview GET /api/stats/overview
t stats-test GET /api/stats/test-result
t stats-content GET /api/stats/content-type
t stats-group GET /api/stats/group
t stats-mode GET /api/stats/test-mode

echo ""
echo "===== Sources ====="
t sources-list GET "/api/sources?page=1&page_size=5"
t sources-groups GET /api/sources/groups
t sources-domain GET "/api/sources/by-domain?domain_key=test"
t validate-ok POST /api/sources/validate '{"source_json":"{\"bookSourceUrl\":\"https://t.com\",\"bookSourceName\":\"T\"}"}'
t validate-bad POST /api/sources/validate '{"source_json":"invalid"}'
t source-create POST /api/sources '{"source_json":"{\"bookSourceUrl\":\"https://crud.com\",\"bookSourceName\":\"CRUD\",\"source_type\":\"book\"}"}'

SID=$(curl -s "$BASE/api/sources?page=1&page_size=10&search=CRUD" | python -c "import sys,json; d=json.load(sys.stdin); items=d.get('data',{}).get('items',[]); print(items[0]['id'] if items else '')" 2>/dev/null)
echo "  Source ID: $SID"
if [[ -n "$SID" ]]; then
  t source-get GET "/api/sources/$SID"
  t source-update PUT "/api/sources/$SID" '{"source_json":"{\"bookSourceUrl\":\"https://crud.com\",\"bookSourceName\":\"CRUD2\",\"source_type\":\"book\"}"}'
  t source-toggle PATCH "/api/sources/$SID/toggle?enabled=false"
  t source-toggle2 PATCH "/api/sources/$SID/toggle?enabled=true"
  t source-export POST "/api/sources/$SID/export"
  t source-delete DELETE "/api/sources/$SID"
fi

echo ""
echo "===== Batch ====="
curl -s -X POST "$BASE/api/sources" -H 'Content-Type: application/json' -d '{"source_json":"{\"bookSourceUrl\":\"https://b1.com\",\"bookSourceName\":\"B1\",\"source_type\":\"book\"}"}' >/dev/null 2>&1
curl -s -X POST "$BASE/api/sources" -H 'Content-Type: application/json' -d '{"source_json\":\"{\"bookSourceUrl\":\"https://b2.com\",\"bookSourceName\":\"B2\",\"source_type\":\"book\"}"}' >/dev/null 2>&1
IDS=$(curl -s "$BASE/api/sources?page=1&page_size=50&search=B" | python -c "import sys,json; d=json.load(sys.stdin); items=d.get('data',{}).get('items',[]); print(','.join(str(i['id']) for i in items))" 2>/dev/null)
echo "  Batch IDs: $IDS"
if [[ -n "$IDS" ]]; then
  t batch-enable POST /api/sources/batch-action "{\"action\":\"enable\",\"source_ids\":[$IDS]}"
  t batch-export POST /api/sources/batch-export "{\"source_ids\":[$IDS]}"
  t batch-delete POST /api/sources/batch-action "{\"action\":\"delete\",\"source_ids\":[$IDS]}"
fi

echo ""
echo "===== Import ====="
t import-url POST /api/import/url '{"url":"https://example.com/test.json","source_type":"book"}'
t import-github POST /api/import/github '{"url":"https://github.com/test/repo"}'
t import-legado POST /api/import/legado-pull '{"device_id":"none","source_type":"book"}'

echo ""
echo "===== Collections ====="
t collections-list GET "/api/collections?page=1&page_size=5"
t collections-remote GET /api/collections/remote
t collections-fetchall POST /api/collections/fetch-all
t collections-incremental POST /api/collections/incremental

echo ""
echo "===== Devices ====="
t devices-list GET /api/devices
t devices-add POST /api/devices '{"name":"TestDev","address":"192.168.1.100:1122"}'
DEV_ID=$(curl -s "$BASE/api/devices" | python -c "import sys,json; d=json.load(sys.stdin); items=d.get('data',[]); print(items[0]['id'] if items else '')" 2>/dev/null)
echo "  Device ID: $DEV_ID"
if [[ -n "$DEV_ID" ]]; then
  t device-update PUT "/api/devices/$DEV_ID" '{"name":"TestDev2","address":"192.168.1.101:1122"}'
  t device-test POST "/api/devices/$DEV_ID/test-connection"
  t device-push POST "/api/devices/$DEV_ID/push" '{"source_type":"book","source_urls":["https://test.com"]}'
  t device-pull POST "/api/devices/$DEV_ID/pull" '{"source_type":"book"}'
  t device-delete DELETE "/api/devices/$DEV_ID"
fi

echo ""
echo "===== Debug ====="
t debug-compare POST /api/debug/compare '{"source_url":"https://test.com"}'
t debug-optimize POST /api/debug/jar-optimize '{"source_url":"https://test.com"}'

echo ""
echo "=========================================="
echo "  TOTAL: PASS=$PASS  FAIL=$FAIL"
if [[ $FAIL -gt 0 ]]; then echo -e "  FAILED:$ERRORS"; fi
echo "=========================================="
