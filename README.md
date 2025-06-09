# 海康门禁推送服务项目说明

## 项目简介
本项目为“海康门禁推送服务”，基于 Python Flask 实现，支持多种门禁设备推送格式，自动解析、过滤、记录所有有效门禁事件，并同步写入 MySQL 数据库和 JSON 行日志文件，适配生产环境 Docker 部署。

## 主要功能
1. **多格式兼容**：支持 application/json、form-data、multipart/form-data 等多种推送格式，递归解析嵌套 AccessControllerEvent。
2. **数据过滤**：自动过滤心跳包（eventType=heartBeat）、姓名为空或无效的数据，保证日志和数据库只存储有效门禁事件。
3. **日志与数据库同步**：所有有效事件同步写入 MySQL 数据库和 log/record_log.jsonl（JSON 行日志），便于自动化分析和溯源。
4. **详细日志输出**：终端日志详细输出 headers、form、raw data，便于排查设备推送格式和异常。
5. **图片隐私保护**：日志和数据库均不采集图片、图片数量、图片坐标等隐私字段，保障数据合规。
6. **Docker 生产部署**：支持多端口监听、日志目录挂载、时区设置，适配生产环境高可用运维。

## 适用场景
- 企事业单位、园区、楼宇等多品牌门禁设备统一接入、数据归档、自动化分析。
- 生产环境高可用、易运维的门禁事件采集与溯源。
- 需要对接多种推送格式、兼容多厂商设备的门禁数据平台。

## 目录结构
- src/server.py：主服务入口，数据解析、过滤、日志与数据库写入。
- src/run387.py：多端口监听主程序。
- src/utils/file_writer.py：日志写入工具。
- src/typess/record.py：门禁记录数据结构。
- src/requirements.txt：依赖列表。
- src/Dockerfile、docker-compose.yml：Docker 部署配置。
- log/record_log.jsonl：所有有效门禁事件日志（JSON 行格式）。

## 关键配置与注意事项
- **MAX_CONTENT_LENGTH**：Flask 最大请求体 32MB，兼容大体积推送。
- **BadRequest 捕获**：全局捕获 400，输出原始 body 片段，便于排查格式异常。
- **图片字段过滤**：日志与数据库均自动剔除图片相关字段。
- **Docker 部署**：建议使用 docker-compose，挂载 log 目录，保证日志持久化。
- **依赖锁定**：建议 requirements.txt 明确依赖版本，保证本地与容器一致。

## 常见问题排查
- **大体积 multipart/form-data 400**：如遇 400，优先抓包分析推送原始 body，排查设备推送格式。
- **日志/数据库无数据**：请先检查推送格式、过滤规则（心跳包、姓名为空等），再排查数据库连接与日志目录权限。

## 联系与支持
如需扩展字段映射、批量导入、对接更多设备协议，或遇到特殊兼容性问题，请联系项目维护者。

## 字段转移与自定义上传配置说明
1. **字段转移/自定义上传**：如需将门禁事件的特定字段转移到其它表、接口或第三方平台，可在 `src/server.py` 的 `insert_to_mysql` 函数、`write_to_file_json` 函数中自定义字段映射、过滤、转发逻辑。例如：
   - 在 `insert_to_mysql` 增加/修改 SQL 字段映射。
   - 在 `write_to_file_json` 增加字段重命名、结构调整、或调用外部 API 上传。
2. **配置上传字段**：如需灵活配置哪些字段需要上传，可在 `server.py` 中定义允许上传的字段白名单，并在写入数据库/日志前进行过滤。例如：
   - 定义 `ALLOWED_FIELDS = ['deviceName', 'record_date', ...]`，上传前只保留这些字段。
   - 也可通过环境变量或配置文件动态调整上传字段。

## Docker 镜像构建与运行教程
1. **构建镜像**
   ```shell
   cd src
   docker build -t hikvision-access-server .
   ```
2. **使用 docker-compose 一键部署**
   ```shell
   cd ..
   docker-compose up -d
   ```
   - 日志目录会自动挂载到本地 log 目录。
   - 默认监听 286、387 端口。
   - 可通过 `docker-compose logs -f` 查看服务日志。
3. **常用命令**
   - 停止服务：`docker-compose down`
   - 重建镜像：`docker-compose build --no-cache && docker-compose up -d`
   - 查看容器状态：`docker ps`

## 本地运行项目说明
1. **安装依赖**
   ```shell
   cd src
   pip install -r requirements.txt
   ```
2. **启动服务**
   ```shell
   python run387.py
   ```
   - 默认监听 286、387 端口。
   - 日志文件写入 `../log/record_log.jsonl`。
3. **环境要求**
   - Python 3.8 及以上
   - MySQL 数据库可用，配置在 `server.py` 中
   - 建议使用虚拟环境隔离依赖
