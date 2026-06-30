#!/bin/sh
# 移除 nginx 官方镜像自带的 default.conf，避免与模板生成的 hermes.conf 冲突
# （default.conf 作为默认 server 会抢走不匹配 server_name 的请求）
rm -f /etc/nginx/conf.d/default.conf
