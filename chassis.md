下面只讲组网操作：在 3588 底盘 和 调试电脑 上做。当前这台工作电脑不动。
先建立心智模型（30 秒）
调试电脑上的 ROS 节点 ──(TCP 7447)──► 3588 上的 rmw_zenohd（路由器）
                                              ▲
底盘容器里的 ROS 节点 ──(本机 localhost:7447)──┘
每台机器上的 ROS 节点默认连本机的 rmw_zenohd。
跨机时：让调试机上的节点以 client 身份，直接连 3588 的 7447，走同一个路由器，话题才互通。
SSH 只是登录手段，不会自动转发 ROS 话题。
两边必须一致：RMW_IMPLEMENTATION=rmw_zenoh_cpp，以及 同一个 ROS_DOMAIN_ID（没设过就都是 0）。
A. 底盘 3588（先做）
A1. SSH 进容器，确认底盘已在跑
ssh <user>@<3588的局域网IP>
distrobox enter ubuntu24
# 若底盘还没起：
cd ~/chassis_ws && ./quick_start.sh   # 或你平时的 launch
容器里应能看到：
echo $RMW_IMPLEMENTATION          # 应为 rmw_zenoh_cpp
echo $ROS_DOMAIN_ID               # 记下，没有输出=默认 0
ros2 topic list                   # 应有 /cmd_vel、/chassis/odom 等
A2. 确认本机 Zenoh 路由器在跑，且对外监听
# 进程
pgrep -af rmw_zenohd
# 端口：应看到 7447 在听（理想情况是 *:7447 或 [::]:7447，不要只有 127.0.0.1）
ss -lntp | grep 7447
若没有 rmw_zenohd，在容器里单独开一个终端：
source /opt/ros/jazzy/setup.bash
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
ros2 run rmw_zenoh_cpp rmw_zenohd
若 ss 显示只绑了 127.0.0.1:7447，先停掉旧的 rmw_zenohd，再强制 IPv4 全网卡监听：
# 停旧进程后：
export ZENOH_CONFIG_OVERRIDE='listen/endpoints=["tcp/0.0.0.0:7447"]'
ros2 run rmw_zenoh_cpp rmw_zenohd
再查一次：ss -lntp | grep 7447 → 应类似 0.0.0.0:7447。
A3. 记下 IP，并做本机连通性自检
hostname -I | awk '{print $1}'    # 记为 ROBOT_IP，例如 192.168.x.x
在 调试机（下一步）能 ping ROBOT_IP 即可。若 3588 有防火墙，放行 TCP 7447（Ubuntu 示例：sudo ufw allow 7447/tcp）。
底盘侧到这里：底盘 launch + 对外监听的 rmw_zenohd 保持运行即可。
B. 调试电脑（核心配置）
假定调试机已有 ROS 2 Jazzy、ros-jazzy-rmw-zenoh-cpp，且有 ~/fa_w2_ws（没有也可用手动 export）。
B1. 推荐：用仓库脚本（持久写进 ~/.bashrc）
cd ~/fa_w2_ws
./init_repo.sh
# → 配置环境
# → 中间件选 Zenoh
# → Domain ID：与 3588 相同（两边都是 0 就填 0）
# → Zenoh Client：开启，填 ROBOT_IP:7447（例如 192.168.1.50:7447）
# → Session 配置：可用仓库默认 zenoh/DEFAULT_RMW_ZENOH_SESSION_CONFIG.json5
然后：
source ~/.bashrc
# 或新开一个终端
确认环境：
echo $RMW_IMPLEMENTATION
# rmw_zenoh_cpp
echo $ROS_DOMAIN_ID
# 与底盘一致
echo $ZENOH_CONFIG_OVERRIDE
# 应类似：mode="client";connect/endpoints=["tcp/ROBOT_IP:7447"]
重要： 调试机作为 client 直连底盘路由器 时，不要再起本机的 rmw_zenohd（也不要让 bashrc/脚本后台自动起一个连 localhost:7447）。
若本机已有：
pgrep -af rmw_zenohd
# 有的话先停掉，避免连错本地空路由器
kill <pid>
B2. 临时试一次（不改 bashrc）
新终端里：
source /opt/ros/jazzy/setup.bash
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
export ROS_DOMAIN_ID=0    # 与底盘一致；底盘若不是 0 就改成一样
export ZENOH_CONFIG_OVERRIDE='mode="client";connect/endpoints=["tcp/ROBOT_IP:7447"]'
# 把 ROBOT_IP 换成真实 IP

C. 组网验收（按顺序）
全部在 调试机 上做（底盘 launch 与 zenohd 保持运行）。
C1. 网络层
ping -c 3 ROBOT_IP
nc -vz ROBOT_IP 7447
# 成功应提示 Connected / succeeded
nc 失败 → 防火墙 / zenohd 未对外听 / IP 不对；先回到 A2。
C2. 话题发现
ros2 topic list
应能看到底盘侧话题，例如 /cmd_vel、/chassis/odom、/tf（若已开 TF）等。
若几乎为空或只有少数本地节点：Domain / Client 地址 / 本机误起 zenohd。
C3. 订阅（底盘 → 调试机）
ros2 topic hz /chassis/odom
ros2 topic echo /chassis/odom --once
有频率、有数据 → 下行 OK。
C4. 发布（调试机 → 底盘）— 安全低速
人在旁边，确认可急停：
# 确保速度模式
ros2 topic pub --once /chassis/control_mode std_msgs/msg/UInt8 "{data: 1}"
# 短时前进（注意超时 0.5s，-r 20 可持续）
ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.1, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
车动 → 组网成功。停：Ctrl+C，再：
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{}"

对照：两边各自该怎样
项目
3588 底盘
调试机
RMW
rmw_zenoh_cpp
同左
Domain
记下并固定
相同
rmw_zenohd
必须跑，监听 *:7447
不要跑（client 直连时）
Client
不需要
mode=client → tcp/ROBOT_IP:7447
业务进程
底盘 launch
仅 ros2 topic 验收即可

常见失败对照
现象
优先查
nc 不通 7447
3588 zenohd / ss 是否 0.0.0.0 / 防火墙
topic list 空或没有底盘话题
Domain 不一致；调试机未设 Client；本机误起 zenohd
能 list 不能 echo
节点已发现但 QoS/域仍异常；重启两边节点与 zenohd 再试
echo 有数据，pub 车不动
control_mode 是否为 1；是否持续 -r 发布（0.5s 超时）

组网完成标准
调试机上同时满足：
nc ROBOT_IP 7447 通
ros2 topic list 能看到底盘话题
ros2 topic hz /chassis/odom 有数据
调试机 pub /cmd_vel 能驱动真车
做到 4 就说明 Phase 0 组网完成，再往 Isaac / WBC 挂话题即可。
你现场若某一步卡住，把 A2 的 ss -lntp | grep 7447、调试机三个 echo（RMW / DOMAIN / ZENOH_CONFIG_OVERRIDE）、ros2 topic list 摘要 发过来即可继续排查。