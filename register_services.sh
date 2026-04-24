#!/bin/bash
set -e
cd /home/kenzamns/CS/web/agriguard

AUTH_HOST=$(docker inspect agriguard-auth --format '{{.Config.Hostname}}')
FARM_HOST=$(docker inspect agriguard-farm --format '{{.Config.Hostname}}')
DIAG_HOST=$(docker inspect agriguard-diagnosis --format '{{.Config.Hostname}}')
NOTIF_HOST=$(docker inspect agriguard-notification --format '{{.Config.Hostname}}')
GW_HOST=$(docker inspect agriguard-gateway --format '{{.Config.Hostname}}')

curl -s -X PUT http://localhost:8500/v1/agent/service/register -H "Content-Type: application/json" -d "{\"ID\":\"auth-service-1\",\"Name\":\"auth-service\",\"Address\":\"$AUTH_HOST\",\"Port\":8001,\"Tags\":[\"traefik.enable=true\",\"traefik.http.routers.auth.rule=PathPrefix(\`/api/auth\`)\",\"traefik.http.routers.auth.entrypoints=web\",\"traefik.http.routers.auth.priority=100\"],\"Check\":{\"HTTP\":\"http://$AUTH_HOST:8001/api/auth/health/\",\"Interval\":\"10s\",\"Timeout\":\"3s\"}}"

curl -s -X PUT http://localhost:8500/v1/agent/service/register -H "Content-Type: application/json" -d "{\"ID\":\"farm-service-1\",\"Name\":\"farm-service\",\"Address\":\"$FARM_HOST\",\"Port\":8002,\"Tags\":[\"traefik.enable=true\",\"traefik.http.routers.farm.rule=PathPrefix(\`/api/farms\`)\",\"traefik.http.routers.farm.entrypoints=web\",\"traefik.http.routers.farm.priority=100\"],\"Check\":{\"HTTP\":\"http://$FARM_HOST:8002/api/farms/health/\",\"Interval\":\"10s\",\"Timeout\":\"3s\"}}"

curl -s -X PUT http://localhost:8500/v1/agent/service/register -H "Content-Type: application/json" -d "{\"ID\":\"diagnosis-service-1\",\"Name\":\"diagnosis-service\",\"Address\":\"$DIAG_HOST\",\"Port\":8003,\"Tags\":[\"traefik.enable=true\",\"traefik.http.routers.diagnosis.rule=PathPrefix(\`/api/diagnosis\`)\",\"traefik.http.routers.diagnosis.entrypoints=web\",\"traefik.http.routers.diagnosis.priority=100\"],\"Check\":{\"HTTP\":\"http://$DIAG_HOST:8003/api/diagnosis/health/\",\"Interval\":\"10s\",\"Timeout\":\"3s\"}}"

curl -s -X PUT http://localhost:8500/v1/agent/service/register -H "Content-Type: application/json" -d "{\"ID\":\"notification-service-1\",\"Name\":\"notification-service\",\"Address\":\"$NOTIF_HOST\",\"Port\":8004,\"Tags\":[\"traefik.enable=true\",\"traefik.http.routers.notify.rule=PathPrefix(\`/api/notify\`)\",\"traefik.http.routers.notify.entrypoints=web\",\"traefik.http.routers.notify.priority=100\"],\"Check\":{\"HTTP\":\"http://$NOTIF_HOST:8004/api/notify/health/\",\"Interval\":\"10s\",\"Timeout\":\"3s\"}}"

curl -s -X PUT http://localhost:8500/v1/agent/service/register -H "Content-Type: application/json" -d "{\"ID\":\"gateway-service-1\",\"Name\":\"gateway-service\",\"Address\":\"$GW_HOST\",\"Port\":8080,\"Tags\":[\"traefik.enable=true\",\"traefik.http.routers.gateway.rule=PathPrefix(\`/\`)\",\"traefik.http.routers.gateway.entrypoints=web\",\"traefik.http.routers.gateway.priority=1\"],\"Check\":{\"HTTP\":\"http://$GW_HOST:8080/health/\",\"Interval\":\"10s\",\"Timeout\":\"3s\"}}"

echo "✅ All services registered in Consul"
curl -s http://localhost:8500/v1/agent/services | python3 -m json.tool | grep '"Name"'
