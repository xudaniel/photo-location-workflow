# Maps and Street View / 地图与街景

Available on `main` for the next release. / 已在 `main` 实现，将随下个版本发行。

The map workbench connects manual inspection to saved evidence. Basic links, URL parsing, KML and reports need **no Google API key**, no new runtime dependency and no automated map requests. External maps open only when clicked. / 地图工作台把实际查看与证据记录连接起来；基础链接、解析、KML 和报告无需 Google 密钥及新运行依赖，不自动请求外部地图。

## 1. Save an inspected view / 保存已查看视角

Choose a candidate, open the map, then fill in the left-hand viewpoint form. / 选择候选并实际查看地图，再填写左侧视角表单。

- Keep the exact inspected source URL and select the tool. / 保存实际查看的来源链接，选择工具。
- For Google Street View, optionally enter latitude/longitude, panorama ID, heading (-180–360°), pitch (-90–90°), and horizontal FOV (10–100°). / Google 街景可补坐标、全景 ID、朝向、俯仰与水平视野。
- Enter the displayed capture year (`YYYY`), month (`YYYY-MM`), or explicitly `unknown`. Attribution is separate. Save time is recorded independently. / 如实填写显示的拍摄年、月份或 unknown；提供者与保存时间分别记录，不补猜月份。
- Record imagery availability as `unreviewed`, `available`, or `unavailable`; this is a manual observation, not a live availability check. / 人工记录未检查、可查看或无影像，程序不会自动探测覆盖。
- Describe specific matches, uncertainty and contradictions. Attach a reference capture to use paired image annotation. / 记录具体吻合、不确定或矛盾点；附截图后可使用双图编号标注。
- Select an existing reference / Street View evidence item to correct its view metadata. Previous view, date, attribution and time remain in history; the conclusion returns to `candidate`. Review the observation separately to change its verdict. / 可修订已有证据的视角、日期与署名；保留旧记录并恢复候选等级。判断结果另通过复审修改。

### What “reopen” means / “重开”的含义

| Mode / 模式 | Behavior / 行为 |
| --- | --- |
| `panorama_id` | Requests that Google panorama and saved camera parameters; IDs can expire. If coordinates are also saved, Google may fall back to another nearby panorama. / 请求指定全景；ID 可能失效，有坐标时可能回退到其他附近影像。 |
| `nearest_panorama` | Requests imagery nearest the saved coordinate, with saved camera parameters; imagery may change. / 按坐标请求附近全景，不保证每次是同一张。 |
| `map_center` | Opens Google satellite / terrain centered on the saved coordinate at zoom 17. This does not preserve a historical satellite capture or exact 3D camera. / 定位到坐标的卫星或地形图，不固定历史影像或三维相机。 |
| `saved_link` | Opens the original link as supplied. Its destination and continued availability depend on the provider. / 原样打开保存链接，目标及有效期由平台决定。 |

Only documented Google `api=1` URL parameters are parsed. Short links, opaque browser `data=` payloads, ambiguous duplicate parameters and unsupported country domains are retained without inferred fields. An `@lat,lon` camera center is **not** treated as a landmark's position. The candidate form also refuses to infer a place position from a panorama viewpoint. / 仅解析官方标准 api=1 参数；短链、复杂 data 字段、多值歧义及未支持域名不猜测。相机中心不等同于地点坐标，候选表单不自动采用街景相机位置。

## 2. Pin candidates / 固定候选位置

Save coordinates, a Google Place ID, an inspected map-sharing URL, and provenance / uncertainty. Coordinates must come as a valid pair. If a Place ID exists, it is used to identify the search result; the query remains a fallback. / 保存坐标、Place ID、分享链接及位置依据。坐标需成对有效；Place ID 优先指向地点，搜索词保留为回退。

Satellite, terrain, nearby panorama and OpenStreetMap links use the saved coordinates. The Google shortlist includes only candidates with Place IDs, with a maximum of 20 distinct IDs and a 2048-character URL limit; it is not an automatically geocoded list. All candidates remain visible locally. / 卫星、地形、附近街景和 OSM 使用已存坐标；Google 清单仅包含带 Place ID 的候选，最多 20 个不同 ID，且链接最长 2048 字符，超限时不显示清单入口，本地候选仍完整保留。

## 3. Cross-check terrain and alternate imagery / 跨地图核对

Google Earth and Mapillary buttons open the tool home pages. Locate the relevant view manually and record its actual share link as a new evidence item with the appropriate tool. The app does not claim to transfer a precise camera pose into either tool. / Earth 和 Mapillary 按钮打开首页；请定位后把真实分享链接存为对应工具的证据，不声称自动同步精确相机视角。

Use **Export all candidates as KML → Earth** to download coordinate markers for import into a KML-capable map application. Only candidates with coordinates are exported; they are explicitly marked **unverified**. Names, addresses and address-source URLs are included. Export itself stays local; importing into an external service shares those fields with that service. / KML 导出仅包含有坐标的候选，并标明未核实，附名称、地址及地址来源。导出在本机完成；导入外部服务时会向该服务提供这些字段。

Keep the observed image date and contributor for each source. Compare buildings, road geometry, retaining walls, vegetation, mountain profiles and shoreline. Preserve conflicting details. Two platforms may reuse the same underlying imagery; no automatic independent-source count or confidence upgrade is performed. / 分别记录日期和署名，对照建筑、道路、挡墙、植被、山形与湖岸，保留反例；平台数量不等于独立证据数量。

## CLI examples / 命令示例

For an existing investigation, replace every placeholder with actually inspected material. / 对已有调查操作；占位符均须替换为实际核对资料。

```bash
photo-locate map-parse 'https://www.google.com/maps/search/?api=1&query=0,0'
# 0,0 is a syntax example only, not an inferred location.
# 0,0 仅演示语法，不代表推定地点。

photo-locate map-location cases/trip --candidate c1 \
  --shared-url 'https://www.google.com/maps/YOUR_INSPECTED_PLACE' \
  --notes 'Coordinates and Place ID not yet checked / 坐标与地点 ID 尚未核对'

# Attach to an existing Street View evidence record / 附到已有街景证据。
photo-locate map-view cases/trip --evidence e2 --tool google_streetview \
  --original-url 'https://www.google.com/maps/YOUR_INSPECTED_VIEW' \
  --captured unknown --availability unreviewed --provider 'Contributor name'

photo-locate map-links cases/trip
# Requires saved candidate coordinates / 需要先保存候选坐标。
photo-locate map-links cases/trip --kml output/candidates.kml
```

`map-location` also accepts `--latitude`, `--longitude`, `--place-id`; `map-view` also accepts `--latitude`, `--longitude`, `--pano`, `--heading`, `--pitch`, `--fov`. Other tools: `google_satellite`, `google_terrain`, `google_earth`, `mapillary`, `openstreetmap`, `other`. Non-Google Street View tools do not accept Google camera parameters. / 以上参数补齐位置与视角；其他工具不使用 Google 街景相机参数。

HTML / PDF reports include saved view parameters, availability, capture date, attribution, replay/source links and view correction history, alongside existing paired image details. Fields are optional under schema 1; old cases remain readable. / 报告附视角参数、覆盖状态、拍摄日期、署名、重开与来源链接、视角修订历史和原有双图细节；schema 1 下字段可选，兼容旧调查。

## Official references / 官方参考

- [Google Maps URLs](https://developers.google.com/maps/documentation/urls/get-started): supported search, basemap, shortlist and Street View parameters; no API key for URL launching.
- [Street View metadata](https://developers.google.com/maps/documentation/streetview/metadata): variable date precision and expiring panorama IDs. The project does **not** call this API or fetch its metadata.
- [Mapillary introduction](https://help.mapillary.com/hc/en-us/articles/115001770269-An-Introduction-to-Mapillary): crowdsourced street-level imagery; coverage varies.
