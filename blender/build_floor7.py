# Dựng tầng 7 IKIGAI Building từ ảnh CCTV. Chạy:
#   /Applications/Blender.app/Contents/MacOS/Blender -b -P blender/build_floor7.py
# Xuất: blender/floor7.blend + assets/floor7.glb
# shortcut: kích thước ước lượng bằng mắt từ camera, thay số trong phần LAYOUT khi có bản vẽ mặt bằng.
import bpy, bmesh, math, os, mathutils, random
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
floor_root = bpy.data.objects.new("Floor7", None)
scene.collection.objects.link(floor_root)


# ---------- vật liệu ----------
def mat(name, rgb, alpha=1.0, rough=0.6, metal=0.0, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = (*rgb, alpha)   # màu trong viewport Solid của Blender
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Alpha"].default_value = alpha
    if alpha < 1:
        try: m.blend_method = "BLEND"
        except Exception: pass
    if emit:
        key = "Emission Color" if "Emission Color" in b.inputs else "Emission"
        b.inputs[key].default_value = (*rgb, 1)
        if "Emission Strength" in b.inputs:
            b.inputs["Emission Strength"].default_value = emit
    return m

M = dict(
    wood=mat("wood", (0.76, 0.58, 0.36)), floor=mat("floor", (0.72, 0.52, 0.28), rough=0.4),
    marble=mat("marble", (0.85, 0.83, 0.78), rough=0.2), concrete=mat("concrete", (0.45, 0.45, 0.47)),
    wall=mat("wall", (0.86, 0.87, 0.88)), dark=mat("dark", (0.12, 0.13, 0.14)),
    black=mat("black", (0.03, 0.03, 0.035), rough=0.4), white=mat("white", (0.92, 0.92, 0.92)),
    grey=mat("grey", (0.55, 0.57, 0.6)), blue=mat("blue", (0.1, 0.45, 0.8)),
    green=mat("green", (0.05, 0.5, 0.42)), teal=mat("teal", (0.1, 0.35, 0.33)),
    glass=mat("glass", (0.75, 0.88, 0.92), alpha=0.16, rough=0.03),
    window=mat("window", (0.9, 0.95, 1.0), alpha=0.35, rough=0.05),
    metal=mat("metal", (0.6, 0.58, 0.55), rough=0.3, metal=0.9),
    darkwood=mat("darkwood", (0.3, 0.19, 0.12)), pink=mat("pink", (0.95, 0.45, 0.65)),
    screen=mat("screen", (0.25, 0.45, 0.9), emit=1.5), red=mat("red", (0.7, 0.15, 0.12)),
    yellow=mat("yellow", (0.85, 0.7, 0.2)), tabletop=mat("tabletop", (0.58, 0.47, 0.37), rough=0.5), velvet=mat("velvet", (0.012, 0.11, 0.075), rough=0.9),
    navy=mat("navy", (0.07, 0.16, 0.36), rough=0.5), scr=mat("scr", (0.02, 0.035, 0.07), rough=0.2, emit=0.5), scr_hi=mat("scr_hi", (0.1, 0.16, 0.3), rough=0.2, emit=1.2),
    scr_acc=mat("scr_acc", (0.2, 0.75, 0.45), rough=0.2, emit=1.5), meshdark=mat("meshdark", (0.05, 0.05, 0.055), rough=0.8), oak=mat("oak", (0.6, 0.42, 0.24), rough=0.5), cream=mat("cream", (0.78, 0.7, 0.52), rough=0.8), tint=mat("tint", (0.05, 0.06, 0.07), alpha=0.5, rough=0.05),
    tile=mat("tile", (0.45, 0.58, 0.78), rough=0.6), firered=mat("firered", (0.7, 0.06, 0.05), rough=0.4), espresso=mat("espresso", (0.07, 0.045, 0.03), rough=0.5), exitgreen=mat("exitgreen", (0.1, 0.9, 0.35), emit=2.0), walnut=mat("walnut", (0.2, 0.15, 0.11), rough=0.45), slate=mat("slate", (0.27, 0.3, 0.34)), steel=mat("steel", (0.78, 0.78, 0.78), rough=0.35, metal=0.3),
)

# sàn gỗ: ảnh vân ván sinh bằng code (16 ván / 3.2 m, ván chạy theo trục y), lưu vào assets để GLB nhúng theo
def plank_image(path, base=(0.62, 0.46, 0.30), n=16, size=512):
    rng = np.random.default_rng(7)
    px = np.ones((size, size, 4), np.float32)
    pw = size // n
    for i in range(n):
        off = int(rng.integers(0, size))
        col = np.empty((size, 1, 3), np.float32)
        for a, b in ((0, size // 2), (size // 2, size)):          # 2 tấm ván mỗi cột, mỗi tấm một sắc độ
            col[a:b] = np.array(base) * (1 + rng.uniform(-0.1, 0.08))
        col = np.roll(col, off, axis=0)
        streak = 1 + rng.normal(0, 0.018, (1, pw, 1))             # thớ gỗ chạy dọc ván
        px[:, i * pw:(i + 1) * pw, :3] = col * streak
        px[:, i * pw, :3] *= 0.72                                  # khe giữa hai ván
        for j in (off, (off + size // 2) % size):
            px[j, i * pw:(i + 1) * pw, :3] *= 0.72                 # mối nối đầu ván
    img = bpy.data.images.new("planks", size, size, alpha=False)
    img.pixels.foreach_set(np.clip(px, 0, 1).ravel())
    img.filepath_raw, img.file_format = path, "PNG"
    img.save()
    return img

os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
M["planks"] = mat("planks", (0.45, 0.27, 0.11), rough=0.45)
_t = M["planks"].node_tree.nodes.new("ShaderNodeTexImage")
_t.image = plank_image(os.path.join(ROOT, "assets", "tex_floor.png"))
M["planks"].node_tree.links.new(_t.outputs["Color"], M["planks"].node_tree.nodes["Principled BSDF"].inputs["Base Color"])
# tường sơn sần: normal map hạt mịn sinh bằng code (ô ảnh 0.25 m, lặp liền mạch)
def stucco_normal(path, size=256):
    rng = np.random.default_rng(3)
    k = np.hypot(np.fft.fftfreq(size)[:, None], np.fft.fftfreq(size)[None, :])
    h = np.real(np.fft.ifft2(np.fft.fft2(rng.normal(size=(size, size))) * np.exp(-(k / 0.12) ** 2) * (k / 0.05) / (1 + k / 0.05)))   # lọc dải: hạt cỡ 0.5–1 cm
    h /= h.std()
    dx, dy = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5, (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    n = np.dstack((-dx * 1.2, -dy * 1.2, np.ones_like(h)))
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    px = np.ones((size, size, 4), np.float32); px[..., :3] = n * 0.5 + 0.5
    img = bpy.data.images.new("stucco_n", size, size, alpha=False, is_data=True)
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw, img.file_format = path, "PNG"
    img.save()
    return img

_nt = M["wall"].node_tree
_t = _nt.nodes.new("ShaderNodeTexImage"); _t.image = stucco_normal(os.path.join(ROOT, "assets", "tex_wall_n.png"))
_t.image.colorspace_settings.name = "Non-Color"
_n = _nt.nodes.new("ShaderNodeNormalMap"); _n.inputs["Strength"].default_value = 0.35
_nt.links.new(_t.outputs["Color"], _n.inputs["Color"]); _nt.links.new(_n.outputs["Normal"], _nt.nodes["Principled BSDF"].inputs["Normal"])
_nt.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.85
# trần chỉ nhìn thấy từ bên dưới (lọc mặt sau) để góc nhìn từ trên xuống vẫn thấy được bên trong
M["ceil"] = mat("ceil", (0.9, 0.9, 0.9), rough=0.9); M["ceilc"] = mat("ceilc", (0.42, 0.41, 0.4), rough=0.95)
M["ceil"].use_backface_culling = M["ceilc"].use_backface_culling = True

def quad(name, x0, y0, x1, y1, z, m, up=True):
    """Tấm phẳng nằm ngang; UV theo toạ độ thế giới (3.2 m / ô ảnh) để vân sàn liền mạch giữa các phòng."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    f = bm.faces.new([bm.verts.new((x, y, z)) for x, y in (pts if up else pts[::-1])])
    uv = bm.loops.layers.uv.new()
    for l in f.loops: l[uv].uv = (l.vert.co.x / 3.2, l.vert.co.y / 3.2)
    bm.to_mesh(me); bm.free(); me.materials.append(M[m])
    o = bpy.data.objects.new(name, me); o.parent = floor_root
    scene.collection.objects.link(o)
    return o

# ---------- hình khối dùng chung (1 mesh / vật liệu để GLB nhẹ) ----------
_meshes = {}
def mesh(shape, m, size=None):
    """box | cyl | wedge (lăng trụ tam giác, mũi nhọn chúc xuống) | trap (hộp thu hẹp phía trên) | rbox (hộp bo tròn, kích thước thật)."""
    key = (shape, m, size)
    if key not in _meshes:
        me = bpy.data.meshes.new(f"{shape}_{m}")
        bm = bmesh.new()
        if shape == "cyl":
            bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.5, radius2=0.5, depth=1)
        else:
            bmesh.ops.create_cube(bm, size=1)
        if shape == "wedge":
            for v in bm.verts:
                if v.co.z < 0: v.co.x, v.co.y = 0, 0.3   # chóp ngược: chụm về một điểm lệch ra phía trước
            bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
        elif shape == "trap":  # mép trên hẹp hơn và lệch: đỉnh cao phía +x, thấp dần về -x
            for v in bm.verts:
                if v.co.z > 0:
                    if v.co.x > 0: v.co.x = 0.4
                    else: v.co.x, v.co.z = -0.28, 0.32
        elif shape == "tbox":  # hộp kích thước thật có UV theo mét (0.25 m / ô ảnh) để vân tường không bị kéo giãn
            for v in bm.verts:
                v.co.x *= size[0]; v.co.y *= size[1]; v.co.z *= size[2]
            uv = bm.loops.layers.uv.new()
            for f in bm.faces:
                ax = (0, 1) if abs(f.normal.z) > 0.5 else (1, 2) if abs(f.normal.x) > 0.5 else (0, 2)
                for l in f.loops: l[uv].uv = (l.vert.co[ax[0]] * 4, l.vert.co[ax[1]] * 4)
        elif shape == "rbox":  # bo tròn trên kích thước thật để bán kính bo không bị méo theo scale
            for v in bm.verts:
                v.co.x *= size[0]; v.co.y *= size[1]; v.co.z *= size[2]
            bmesh.ops.bevel(bm, geom=bm.edges[:], offset=min(0.14, 0.42 * min(size)), offset_type="OFFSET",
                            segments=5, profile=0.5, affect="EDGES")
            for f in bm.faces: f.smooth = True
        elif shape == "shell":  # vỏ ghế nhựa liền khối: mặt ngồi uốn lên thành lưng, lưng thu hẹp và bo tròn phía trên (kích thước thật, người ngồi hướng +y)
            bm.clear()
            prof = [(0.245, 0.405, 0.2), (0.225, 0.44, 0.225), (0.1, 0.44, 0.23), (-0.05, 0.44, 0.23), (-0.15, 0.447, 0.225),   # (y, z, nửa bề ngang)
                    (-0.205, 0.475, 0.22), (-0.235, 0.53, 0.215), (-0.25, 0.6, 0.21), (-0.265, 0.69, 0.2), (-0.277, 0.77, 0.185),
                    (-0.285, 0.825, 0.16), (-0.289, 0.855, 0.12), (-0.291, 0.868, 0.06)]
            rows = []
            for i, (y, z, w) in enumerate(prof):
                b = min(1, max(0, (i - 3) / 4))   # 0 = mặt ngồi, 1 = lưng
                rows.append([bm.verts.new((w * v, y + 0.05 * b * v * v, z + 0.03 * (1 - b) * v * v)) for v in (-1, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1)])
            faces = [bm.faces.new((r0[j], r0[j + 1], r1[j + 1], r1[j])) for r0, r1 in zip(rows, rows[1:]) for j in range(8)]
            inner = {v for r in rows for v in r}
            bmesh.ops.solidify(bm, geom=faces, thickness=0.014)
            for f in bm.faces:   # hai mặt vỏ mịn, viền mép để phẳng cho khỏi loang bóng
                f.smooth = len({v in inner for v in f.verts}) == 1
        elif shape == "cpanel":  # tấm đứng uốn cong ôm người ngồi, bo góc: size = (bề ngang, độ cong hai mép về +y, chiều cao)
            bm.clear()
            w, c, h = size
            r = min(w, h) * 0.22
            rows = []
            ds = [r * t for t in (0, 0.12, 0.35, 0.65, 1)]   # dồn hàng lưới về hai mép để góc bo tròn đều
            for z in [-h / 2 + d for d in ds] + [0] + [h / 2 - d for d in reversed(ds)]:
                d = min(z + h / 2, h / 2 - z)
                hw = w / 2 - (r - (r * r - (r - d) ** 2) ** 0.5 if d < r else 0)
                rows.append([bm.verts.new((hw * v, c * (hw * v / (w / 2)) ** 2, z)) for v in (-1, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1)])
            faces = [bm.faces.new((r0[j], r0[j + 1], r1[j + 1], r1[j])) for r0, r1 in zip(rows, rows[1:]) for j in range(8)]
            inner = {v for r_ in rows for v in r_}
            bmesh.ops.solidify(bm, geom=faces, thickness=0.018)
            for f in bm.faces:
                f.smooth = len({v in inner for v in f.verts}) == 1
        bm.to_mesh(me); bm.free()
        me.materials.append(M[m])
        _meshes[key] = me
    return _meshes[key]

def part(name, shape, loc, size, m, parent):
    rb = shape in ("rbox", "shell", "cpanel", "tbox")
    o = bpy.data.objects.new(name, mesh(shape, m, tuple(size) if rb else None))
    o.location, o.scale, o.parent = loc, ((1, 1, 1) if rb else size), parent
    scene.collection.objects.link(o)
    return o

def box(name, loc, size, m):  # khối đơn ở toạ độ thế giới
    return part(name, "box", loc, size, m, floor_root)

def place(name, parts, x, y, rot=0, z=0):
    """Đặt 1 asset: parts = [(shape, (x,y,z), (sx,sy,sz), mat)] theo toạ độ cục bộ."""
    e = bpy.data.objects.new(name, None)
    e.location, e.rotation_euler.z, e.parent = (x, y, z), math.radians(rot), floor_root
    scene.collection.objects.link(e)
    for i, (shape, loc, size, m, *rz) in enumerate(parts):  # phần tử thứ 5 (tuỳ chọn): góc xoay quanh z, hoặc bộ (rx, ry, rz)
        o = part(f"{name}.{i}", shape, loc, size, m, e)
        if rz: o.rotation_euler = [math.radians(a) for a in (rz[0] if isinstance(rz[0], tuple) else (0, 0, rz[0]))]
    return e

def legs(dx, dy, h, m, t=0.05):
    return [("box", (sx * dx, sy * dy, h / 2), (t, t, h), m) for sx in (-1, 1) for sy in (-1, 1)]


# ---------- ASSETS (người ngồi hướng +y cục bộ) ----------
DESK = [("box", (0, 0, 0.72), (1.4, 0.75, 0.04), "wood")] + legs(0.65, 0.32, 0.70, "black") + [
    ("box", (0, 0.2, 0.745), (0.22, 0.16, 0.01), "black"),      # chân màn hình
    ("box", (0, 0.2, 0.84), (0.04, 0.04, 0.18), "black"),
    ("box", (0, 0.2, 1.08), (0.72, 0.03, 0.40), "black"),       # màn hình
    ("box", (0, 0.183, 1.08), (0.68, 0.005, 0.36), "screen"),
    ("box", (0, -0.15, 0.75), (0.42, 0.14, 0.02), "dark"),      # bàn phím
]
def office_chair(m):
    return [("cyl", (0, 0, 0.04), (0.6, 0.6, 0.04), "black"), ("cyl", (0, 0, 0.25), (0.06, 0.06, 0.4), "metal"),
            ("box", (0, 0, 0.48), (0.5, 0.5, 0.08), m), ("box", (0, -0.25, 0.85), (0.46, 0.06, 0.62), m)]
CHAIR_BLACK, CHAIR_WHITE, CHAIR_BLUE = office_chair("black"), office_chair("white"), office_chair("blue")
MEETING_TABLE = [("rbox", (0, 0, 0.74), (1.2, 3.0, 0.03), "tabletop")] + legs(0.56, 1.46, 0.725, "black", 0.06) + [
    ("box", (-0.56, 0, 0.7), (0.04, 2.86, 0.05), "black"), ("box", (0.56, 0, 0.7), (0.04, 2.86, 0.05), "black"),          # khung thép dưới mặt bàn
    ("box", (0, -1.46, 0.7), (1.06, 0.04, 0.05), "black"), ("box", (0, 1.46, 0.7), (1.06, 0.04, 0.05), "black"),
    ("box", (0, 0, 0.5), (0.03, 2.2, 0.35), "dark"),             # tấm che dây dưới bàn
    ("box", (0, 0, 0.7565), (0.16, 0.4, 0.003), "metal"),        # hộp ổ cắm giữa bàn: viền, lòng hộp, nắp bật đang mở
    ("box", (0, 0, 0.7585), (0.12, 0.36, 0.002), "dark"),
    ("box", (0.045, 0, 0.8), (0.11, 0.36, 0.006), "metal", (0, -65, 0))]
# ghế lưới công thái học: đệm ngồi bo tròn, lưng lưới uốn cong viền đen, đỡ thắt lưng, tay vịn chữ T, chân sao 5 cánh có bánh xe
def mesh_chair(seat, back, base, headrest=False):
    return [p for a in (18, 90, 162, 234, 306) for c, s in [(math.cos(math.radians(a)), math.sin(math.radians(a)))] for p in (
        ("box", (0.155 * c, 0.155 * s, 0.085), (0.3, 0.045, 0.028), base, (0, 10, a)),                    # cánh chân sao
        ("cyl", (0.3 * c, 0.3 * s, 0.0275), (0.055, 0.055, 0.045), "black", (90, 0, a)))] + [             # bánh xe
        ("cyl", (0, 0, 0.11), (0.08, 0.08, 0.07), base), ("cyl", (0, 0, 0.28), (0.045, 0.045, 0.28), "metal"),      # ổ trục + ty hơi
        ("box", (0, -0.02, 0.425), (0.22, 0.3, 0.04), "black"),                                           # cơ cấu dưới đệm
        ("rbox", (0, 0, 0.475), (0.5, 0.48, 0.07), seat),                                                 # đệm ngồi
        ("box", (0, -0.245, 0.59), (0.07, 0.035, 0.36), "black", (14, 0, 0)),                             # xương lưng
        ("cpanel", (0, -0.285, 0.87), (0.48, 0.06, 0.58), "black", (8, 0, 0)),                            # khung lưng
        ("cpanel", (0, -0.268, 0.87), (0.43, 0.054, 0.53), back, (8, 0, 0)),                              # lưới lưng (mặt trước)
        ("cpanel", (0, -0.302, 0.87), (0.43, 0.054, 0.53), back, (8, 0, 0)),                              # lưới lưng (mặt sau)
        ("box", (0, -0.285, 0.7), (0.3, 0.03, 0.07), "black")] + [p for sx in (-1, 1) for p in (          # đỡ thắt lưng
        ("box", (sx * 0.275, -0.06, 0.585), (0.035, 0.05, 0.2), "black"),                                 # trụ tay vịn
        ("rbox", (sx * 0.275, -0.03, 0.695), (0.075, 0.26, 0.03), "black"))] + ([                         # đệm tay vịn
        ("box", (0, -0.335, 1.2), (0.05, 0.03, 0.14), "black", (8, 0, 0)),                                # cổ tựa đầu
        ("cpanel", (0, -0.33, 1.31), (0.3, 0.035, 0.15), back, (4, 0, 0))] if headrest else [])           # tựa đầu
MEET_CHAIR = mesh_chair("blue", "blue", "metal")
WORK_CHAIR, WORK_CHAIR_W = mesh_chair("black", "meshdark", "black", True), mesh_chair("grey", "white", "white", True)
# bàn ăn pantry: mặt gỗ sẫm, 4 chân thép đen ở góc, tấm ngăn đen giữa gầm kiêm chân bàn (tấm mỏng đặt ngang bàn, từ sàn lên mặt bàn)
DINING_TABLE = [("rbox", (0, 0, 0.74), (1.0, 2.6, 0.04), "walnut")] + legs(0.46, 1.26, 0.72, "black", 0.06) + [
    ("box", (0, 0, 0.36), (0.7, 0.03, 0.72), "black")]
# ghế ăn: vỏ nhựa trắng liền khối (mặt ngồi uốn lên thành lưng), 4 chân gỗ tròn choãi ra từ gầm ghế
PANTRY_CHAIR = [("shell", (0, 0, 0), (1, 1, 1), "white"), ("box", (0, 0, 0.425), (0.3, 0.3, 0.02), "grey")] + [
    ("cyl", (sx * 0.175, sy * 0.165, 0.213), (0.03, 0.03, 0.45), "wood", (sy * 11, sx * -11, 0)) for sx in (-1, 1) for sy in (-1, 1)]
# ghế gỗ đệm xanh ở đầu bàn: chân tròn, hai chân sau vươn lên đỡ thanh tựa cong ôm ra hai bên như tay vịn
WOOD_CHAIR = [("rbox", (0, 0, 0.45), (0.46, 0.44, 0.06), "blue"), ("cpanel", (0, -0.25, 0.74), (0.58, 0.18, 0.07), "wood")] + [p for sx in (-1, 1) for p in (
    ("cyl", (sx * 0.19, 0.17, 0.215), (0.035, 0.035, 0.43), "wood", (-4, sx * -4, 0)),
    ("cyl", (sx * 0.2, -0.2, 0.365), (0.035, 0.035, 0.74), "wood", (5, sx * -3, 0)))]
# quầy bar gỗ: mặt dày + tấm đổ thác ở đầu nam (y cục bộ âm), đầu bắc tựa vào trụ tường
BAR = [("box", (0, 0, 1.02), (0.75, 2.7, 0.06), "wood"), ("box", (0, -1.32, 0.495), (0.75, 0.06, 0.99), "wood")]
# ghế bar nhựa trắng: mặt ngồi cao bo tròn, tựa lưng thấp uốn cong, 4 chân hơi choãi có thanh gác chân
STOOL = [("rbox", (0, 0, 0.75), (0.4, 0.38, 0.045), "white"), ("cpanel", (0, -0.185, 0.9), (0.4, 0.045, 0.2), "white"),
         ("box", (-0.15, -0.18, 0.8), (0.03, 0.03, 0.1), "white"), ("box", (0.15, -0.18, 0.8), (0.03, 0.03, 0.1), "white")] + [
    ("box", (sx * 0.175, sy * 0.165, 0.365), (0.035, 0.035, 0.735), "white", (sy * 4, sx * -4, 0)) for sx in (-1, 1) for sy in (-1, 1)] + [
    ("box", (0, 0.185, 0.3), (0.37, 0.03, 0.03), "white"), ("box", (-0.185, 0, 0.42), (0.03, 0.36, 0.03), "white"), ("box", (0.185, 0, 0.42), (0.03, 0.36, 0.03), "white")]
def armchair(arm):
    """Ghế bành nhung xanh: đệm thấp rộng, gối lưng + gối tay vịn một bên bo tròn (arm=+1/-1: bên phải/trái người ngồi)."""
    return [("rbox", (0, 0, 0.21), (0.98, 0.95, 0.42), "velvet"),                               # đệm ngồi phồng
            ("rbox", (0, -0.31, 0.57), (0.98, 0.33, 0.36), "velvet"),                           # gối lưng tròn chạy hết bề ngang
            ("rbox", (arm * 0.325, -0.1, 0.57), (0.33, 0.75, 0.36), "velvet")]                  # gối tay vịn ôm một bên
# ghế thư giãn dáng gấp origami: lòng ghế thấp ở giữa, thân chữ V chúc xuống sàn, hai cánh phẳng hai bên, lưng hình thang ngả, chân thép chữ A
WING_CHAIR = [("box", (0, 0.02, 0.44), (0.5, 0.62, 0.09), "velvet", (5, 0, 0)),                # lòng ghế trũng nhẹ so với cánh
              ("wedge", (0, 0.02, 0.245), (0.84, 0.6, 0.45), "velvet"),                        # thân chóp ngược rộng, mũi chạm sàn
              ("trap", (0, -0.38, 0.77), (1.05, 0.09, 0.58), "velvet", (16, 0, 0))] + [p for sx in (-1, 1) for p in (  # lưng ngả, đỉnh lệch một bên
              ("box", (sx * 0.335, 0, 0.5), (0.24, 0.62, 0.08), "velvet", (0, sx * -35, 0)),   # mặt dốc từ lòng ghế lên cánh
              ("box", (sx * 0.62, 0, 0.56), (0.4, 0.62, 0.08), "velvet"))] + [                 # cánh phẳng ngang tầm tay
              ("box", (sx * 0.62 + sd * 0.1, sy * 0.24, 0.26), (0.018, 0.018, 0.56), "metal", (0, sd * -22, 0))  # chân thép chữ A dưới mỗi cánh
              for sx in (-1, 1) for sy in (-1, 1) for sd in (-1, 1)]
SIDE_TABLE = [("cyl", (0, 0, 0.44), (0.45, 0.45, 0.015), "glass"), ("cyl", (0, 0, 0.22), (0.03, 0.03, 0.44), "black"),
              ("cyl", (0, 0, 0.01), (0.3, 0.3, 0.02), "black")]
BOOKSHELF = [("box", (0, 0, 1.4), (0.6, 0.6, 2.8), "teal"), ("box", (0, 0, 0.4), (1.7, 1.0, 0.8), "wood")] \
    + [("box", (0, 0, z), (1.7, 1.0, 0.04), "wood") for z in (1.3, 1.8, 2.3)] \
    + [("box", (sx * (0.45 + 0.1 * i), 0.3 * sy, z + 0.14), (0.08, 0.2, 0.26), c)
       for z in (0.8, 1.3, 1.8) for sx in (-1, 1) for sy in (-1, 1) for i, c in enumerate(("red", "blue", "yellow", "white"))]
# TV 65" trên chân đẩy: trụ nâng + hộp điều khiển, đế 4 càng chữ X có bánh xe (kiểu chân ghế xoay); màn hình quay về +y
TV = [("box", (0, 0.06, 1.35), (1.45, 0.04, 0.83), "black"), ("box", (0, 0.062, 0.93), (1.45, 0.04, 0.012), "metal"),  # màn hình + viền bạc dưới
      ("box", (0, 0.02, 1.35), (0.5, 0.04, 0.35), "black"),                                    # tấm gá sau màn hình
      ("box", (0, 0, 0.74), (0.1, 0.08, 1.24), "black"),                                       # trụ nâng
      ("box", (0, 0.03, 0.52), (0.3, 0.12, 0.16), "black"),                                    # hộp điều khiển
      ("cyl", (0, 0, 0.1), (0.16, 0.16, 0.08), "black")] + [p for a in (45, 135, 225, 315) for c, s in [(math.cos(math.radians(a)), math.sin(math.radians(a)))] for p in (
      ("box", (0.22 * c, 0.22 * s, 0.09), (0.44, 0.05, 0.04), "black", a),                     # càng
      ("cyl", (0.46 * c, 0.46 * s, 0.035), (0.07, 0.07, 0.04), "black", (90, 0, a)))]          # bánh xe
VASE = [("cyl", (0, 0, 0.15), (0.16, 0.16, 0.3), "white")] + \
    [("cyl", (dx, dy, 0.48), (0.16, 0.16, 0.12), "pink") for dx, dy in ((0, 0), (0.12, 0.05), (-0.1, 0.08), (0.03, -0.12))]
BIN = [("box", (0, 0, 0.35), (0.4, 0.3, 0.7), "metal"), ("box", (0, 0, 0.72), (0.42, 0.32, 0.04), "blue")]
ELEVATOR = [("box", (0, 0, 1.1), (1.2, 0.06, 2.2), "metal"), ("box", (0, 0, 1.1), (0.02, 0.07, 2.2), "dark"),
            ("box", (0, 0.01, 2.3), (1.6, 0.1, 0.2), "darkwood"), ("box", (-0.72, 0.01, 1.1), (0.2, 0.1, 2.2), "darkwood"),
            ("box", (0.72, 0.01, 1.1), (0.2, 0.1, 2.2), "darkwood")]
DOOR = [("box", (0, 0, 1.05), (0.9, 0.05, 2.1), "dark")]
# cửa chống cháy ra thang thoát hiểm: cánh + khuôn gỗ nâu sẫm, tay nắm; mặt quay về +y cục bộ
FIRE_DOOR = [("box", (0, 0, 1.1), (1.1, 0.12, 2.2), "espresso"), ("box", (0, 0.045, 1.06), (0.94, 0.05, 2.1), "darkwood"),
             ("box", (-0.36, 0.085, 1.05), (0.12, 0.04, 0.03), "metal")]
# cửa thoát hiểm: cánh xám xanh, khuôn gỗ, tay nắm, biển EXIT xanh phía trên
# ổ điện âm tường: mặt trắng vuông, 2 khe cắm; mặt quay về +y cục bộ
OUTLET = [("box", (0, 0.005, 0), (0.086, 0.01, 0.086), "white"), ("box", (-0.012, 0.011, 0), (0.008, 0.002, 0.022), "dark"),
          ("box", (0.012, 0.011, 0), (0.008, 0.002, 0.022), "dark")]
EXIT_DOOR = [("box", (0, 0, 1.1), (1.12, 0.08, 2.2), "wood"), ("box", (0, 0.03, 1.07), (0.98, 0.05, 2.1), "slate"),
             ("box", (-0.38, 0.07, 1.05), (0.12, 0.04, 0.03), "metal"), ("box", (0.05, 0.05, 2.45), (0.5, 0.04, 0.16), "green")]
BOARD = [("box", (0, 0, 1.5), (1.2, 0.04, 1.0), "blue")]


# ---------- tường ----------
H = 2.8
HC = 3.4                               # trần bê tông lộ của khu làm việc, cao hơn trần thạch cao của dải phòng + hành lang
def wall(name, x1, y1, x2, y2, kind="wall", inside=(0, 0), bays=None, punched=False):
    """Tường thẳng theo trục. kind: wall | glass (vách kính) | window (cửa sổ ngoài). punched: cửa sổ từng ô trên tường đặc (trụ tường giữa các ô, mảng tường phía trên, rèm màu kem)."""
    cx, cy, lx, ly = (x1 + x2) / 2, (y1 + y2) / 2, abs(x2 - x1) or 0.1, abs(y2 - y1) or 0.1
    if kind == "wall":
        part(name, "tbox", (cx, cy, H / 2), (lx, ly, H), "wall", floor_root); return
    sill = 0.12 if kind == "window" else 0.0   # cửa sổ gần như sát sàn
    hd = 0.5 if punched else 0.0               # mảng tường đặc phía trên ô cửa
    blind = "cream" if punched else "white"
    frame = "white" if kind == "window" else "dark"
    n = bays or max(1, round(max(lx, ly) / 1.5))   # số ô (mặc định ~1.5 m/ô)
    if sill: box(name + ".sill", (cx, cy, sill / 2), (lx, ly, sill), "wall")
    box(name + ".pane", (cx, cy, (H - hd + sill) / 2), (lx * 0.999 if lx > 0.1 else 0.03, ly * 0.999 if ly > 0.1 else 0.03, H - hd - sill), kind)
    if punched:
        part(name + ".top", "tbox", (cx, cy, H - hd / 2), (lx, ly, hd), "wall", floor_root)
        box(name + ".transom", (cx, cy, 0.95), (lx if lx > 0.1 else 0.05, ly if ly > 0.1 else 0.05, 0.05), "white")   # đố ngang chia ô cửa
    else:
        box(name + ".top", (cx, cy, H - 0.04), (lx, ly, 0.08), frame)
    if kind == "window":  # rèm sáo: lá mảnh sát nhau + dây nâng + dây kéo (inside = hướng vào trong phòng)
        for k in range(int((H - hd - sill - 0.15) / 0.04)):
            box(f"{name}.slat{k}", (cx, cy, sill + 0.06 + k * 0.04), (lx if lx > 0.1 else 0.015, ly if ly > 0.1 else 0.015, 0.004), blind)
        L = max(lx, ly)
        for j in range(int(L / 0.75)):
            t = (j + 0.5) * 0.75 / L
            box(f"{name}.slat.cord{j}", (x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, (H - hd + sill) / 2), (0.005, 0.005, H - hd - sill - 0.1), "white")
        # dây kéo: mỗi ô rèm một dây, sát mép phải khi đứng trong phòng nhìn ra (inside = hướng vào trong phòng)
        right_is_end = (-inside[1]) * (x2 - x1) + inside[0] * (y2 - y1) > 0
        for i in range(n):
            edge = 0.33 if punched else 0.12
            t = ((i + 1) / n - edge / L) if right_is_end else (i / n + edge / L)
            qx, qy = x1 + (x2 - x1) * t + inside[0] * 0.05, y1 + (y2 - y1) * t + inside[1] * 0.05
            box(f"{name}.slat.pull{i}", (qx, qy, (H - hd + 0.9) / 2), (0.006, 0.006, H - hd - 1.0), "white")
            box(f"{name}.slat.knob{i}", (qx, qy, 0.87), (0.02, 0.02, 0.06), "grey")
    for i in range(n + 1):  # đố dọc
        t = i / n
        pw = 0.45 if punched else 0.07
        part(f"{name}.post{i}", "tbox" if punched else "box", (x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, H / 2), (pw if lx > 0.1 else 0.1, pw if ly > 0.1 else 0.1, H), "wall" if punched else frame, floor_root)

# bàn làm việc 4 chỗ (dài theo x cục bộ): mặt gỗ sồi trên khung thép đen, máng đi dây giữa gầm, 2 nắp ổ điện trên mặt;
# mỗi chỗ 2 màn hình trên tay đỡ kẹp bàn (kiểu A: 2 màn ngang chụm vào nhau; kiểu B: 1 màn cong siêu rộng + 1 màn dọc), bàn phím + chuột
TL, TD = 2.36, 1.2
def _monitor(x, sd, w, h, ang, z=1.12):
    """Một màn hình tim x (cục bộ), quay mặt về phía người ngồi (sd=±1 là cạnh bàn có người ngồi), xoay ang độ quanh trục đứng."""
    r = math.radians(ang); nx, ny = -sd * math.sin(r), sd * math.cos(r)   # pháp tuyến mặt màn
    y = sd * 0.2
    return [("box", (x, y, z), (w, 0.025, h), "black", ang),
            ("box", (x + nx * 0.014, y + ny * 0.014, z), (w - 0.03, 0.004, h - 0.03), "scr", ang),
            ("box", (x + nx * 0.017 - sd * math.cos(r) * w * 0.14, y + ny * 0.017 - sd * math.sin(r) * w * 0.14, z + h * 0.05), (w * 0.55, 0.003, h * 0.7), "scr_hi", ang),
            ("box", (x + nx * 0.017 + sd * math.cos(r) * w * 0.3, y + ny * 0.017 + sd * math.sin(r) * w * 0.3, z - h * 0.2), (w * 0.2, 0.003, h * 0.25), "scr_acc", ang)]
def _seat(x0, sd, kind):
    parts = [("box", (x0, sd * 0.1, 0.76), (0.1, 0.08, 0.02), "black"), ("cyl", (x0, sd * 0.1, 0.96), (0.035, 0.035, 0.4), "black"),   # kẹp bàn + trụ tay đỡ
             ("box", (x0, sd * 0.14, 1.12), (0.62, 0.03, 0.04), "black"),                                                         # thanh ngang tay đỡ
             ("box", (x0 - 0.06, sd * 0.47, 0.76), (0.42, 0.14, 0.02), "dark"), ("rbox", (x0 + 0.28, sd * 0.47, 0.765), (0.065, 0.11, 0.03), "black")]   # bàn phím + chuột
    if kind == "A":
        parts += _monitor(x0 - 0.285, sd, 0.55, 0.33, -sd * 9) + _monitor(x0 + 0.285, sd, 0.55, 0.33, sd * 9)
    else:
        parts += _monitor(x0 - sd * 0.17, sd, 0.78, 0.34, -sd * 4) + _monitor(x0 + sd * 0.41, sd, 0.32, 0.54, sd * 14, z=1.15)
    return parts
def work_table_parts(kinds):
    return [("rbox", (0, 0, 0.735), (TL, TD, 0.03), "oak")] + [("box", (sx * (TL / 2 - 0.06), sy * (TD / 2 - 0.06), 0.36), (0.06, 0.06, 0.72), "black") for sx in (-1, 1) for sy in (-1, 1)] + [
        ("box", (0, sy * (TD / 2 - 0.06), 0.695), (TL - 0.18, 0.04, 0.05), "black") for sy in (-1, 1)] + [("box", (sx * (TL / 2 - 0.06), 0, 0.695), (0.04, TD - 0.18, 0.05), "black") for sx in (-1, 1)] + [
        ("box", (0, 0, 0.62), (TL - 0.5, 0.2, 0.06), "black")] + [("box", (sx * 0.55, 0, 0.752), (0.3, 0.12, 0.004), "metal") for sx in (-1, 1)] + [
        p for (sx, sd), k in zip(((-1, -1), (1, -1), (-1, 1), (1, 1)), kinds) for p in _seat(sx * TL / 4, sd, k)]
WORK_TABLES = [work_table_parts(k) for k in ("AABA", "ABAA", "BAAB")]
_wt = [0]

def work_table(name, cx, cy, rot=0):
    """Một bàn 4 chỗ + 4 ghế lưới (2 ghế mỗi cạnh dài)."""
    _wt[0] += 1
    place(name, WORK_TABLES[_wt[0] % 3], cx, cy, rot)
    for i, (sx, sd) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        place(f"{name}.chair{i}", WORK_CHAIR_W if (i + _wt[0] * 3) % 9 == 0 else WORK_CHAIR, *off(cx, cy, rot, sx * TL / 4 + (0.06 if i % 2 else -0.05), sd * (TD / 2 + 0.38)), rot + (0 if sd < 0 else 180) + (12 if i == 1 else -8 if i == 2 else 0))

def off(x, y, rot, dx, dy):  # điểm lệch (dx,dy) cục bộ sau khi xoay
    r = math.radians(rot)
    return x + dx * math.cos(r) - dy * math.sin(r), y + dx * math.sin(r) + dy * math.cos(r)

def workstation(name, x, y, rot, chair):
    place(name + ".desk", DESK, x, y, rot)
    place(name + ".chair", chair, *off(x, y, rot, 0, -0.75), rot)

def bench(name, cx, cy, n, rot=0):
    """Cụm bàn đối lưng tâm (cx,cy), chạy theo hướng rot: mỗi bên n bàn, màn hình quay vào giữa."""
    for i in range(n):
        d = (i - (n - 1) / 2) * 1.4
        workstation(f"{name}.A{i}", *off(cx, cy, rot, d, -0.375), rot, CHAIR_BLACK if i % 3 else CHAIR_WHITE)
        workstation(f"{name}.B{i}", *off(cx, cy, rot, d, 0.375), rot + 180, CHAIR_BLACK)


# ================= LAYOUT (mét, x: tây→đông, y: nam→bắc) =================
# Theo sơ đồ + bản vẽ nội thất của chủ nhà (bản vẽ xoay 180°: trái bản vẽ = đông, trên bản vẽ = nam).
X0, YM, Y1 = 4, 12, 16.5              # mép tây văn phòng, vách ngăn dải phòng phía bắc, mép bắc
XT = X0 - 1.4                          # tường sau TV phòng họp (lõm sang dải hành lang)
ROOM = 6.2                             # bề dài phòng họp = bề dài pantry (ước lượng từ ảnh, thay khi có số đo thật)
XM = XT + ROOM                         # vách kính phòng họp | pantry
X1 = XM + ROOM                         # mép đông: pantry rộng đúng bằng phòng họp (theo chủ nhà)
XB = X1 - 2.525                        # tim quầy bar pantry (bếp sát tường đông, lối đi, rồi quầy)
box("Floor.office", ((X0 + X1) / 2, Y1 / 2, -0.06), (X1 - X0, Y1, 0.1), "floor"); quad("Floor.office.planks", X0, 0, X1, Y1, 0, "planks")
YA, AX = 4.3, X0 - 1.7                 # theo bản vẽ layout của chủ nhà: hành lang dừng ở y=YA; hốc tây-nam (x AX–X0, y 0–YA) thuộc khu làm việc
box("Floor.corridor", (X0 / 2, (YA + Y1) / 2, -0.05), (X0, Y1 - YA, 0.1), "marble")
box("Floor.alcove", ((AX + X0) / 2, YA / 2, -0.06), (X0 - AX, YA, 0.1), "floor"); quad("Floor.alcove.planks", AX, 0, X0, YA, 0, "planks")
YS = YM - 1.6                          # mép nam buồng thang thoát hiểm (kéo xuống để cửa trên tường tây hành lang mở thẳng vào buồng thang)
YL = YS + 1.7                          # mép bắc chiếu nghỉ tầng 7 trong buồng thang
box("Floor.stairs", (-2, (YS + YL) / 2, -0.05), (4, YL - YS, 0.1), "concrete")   # chiếu nghỉ ngang sàn, ngay sau cửa thoát hiểm

# vỏ ngoài văn phòng: cửa sổ nam, đông (phần khu làm việc), bắc; tường đông pantry đặc (bếp + tranh)
wall("Win.S", X0, 0, X1 - 0.9, 0, "window", (0, 1), punched=True)
# góc đông-nam (theo video): cột vuông nhô vào phòng ngay tại góc, treo bảng trắng ở mặt tây; hai bên cột đều là ô cửa sổ
wall("Win.E", X1, 0.9, X1, YM - 3.4, "window", (-1, 0), punched=True)
part("Column.SE", "tbox", (X1 - 0.45, 0.45, HC / 2), (0.9, 0.9, HC), "wall", floor_root)
box("Board.frame", (X1 - 0.91, 0.45, 1.5), (0.02, 0.84, 1.3), "grey"); box("Board.white", (X1 - 0.925, 0.45, 1.5), (0.012, 0.78, 1.24), "white")
wall("Exit.wall", X1, YM - 3.4, X1, YM)                                 # tường đặc: cửa EXIT + bảng ghim, kệ sách đứng phía trước
box("Pin.frame", (X1 - 0.06, YM - 2.2, 1.7), (0.02, 1.0, 1.25), "wood"); box("Pin.board", (X1 - 0.075, YM - 2.2, 1.7), (0.012, 0.92, 1.17), "tile")   # bảng ghim hoạ tiết xanh giữa cửa EXIT và kệ sách
box("Pin.note", (X1 - 0.083, YM - 2.35, 1.6), (0.006, 0.22, 0.3), "white"); box("Pin.flag", (X1 - 0.083, YM - 2.05, 1.95), (0.006, 0.24, 0.24), "navy"); place("D2.exit", EXIT_DOOR, X1 - 0.06, YM - 0.95, 90)
wall("Win.N.meet", XT, Y1, XM, Y1, "window", (0, -1), bays=4); wall("Win.N", XM, Y1, XB - 0.55, Y1, "window", (0, -1), bays=2); wall("Pantry.N", XB - 0.55, Y1, X1, Y1)   # phòng họp dài đúng 3 ô cửa sổ (kể cả phần lõm sang dải hành lang)
wall("Pantry.E", X1, YM, X1, Y1)

# 7.2 hành lang (x 0–4): thang máy tường tây, tủ tường đông, cửa vào văn phòng y 5.6–6.6
wall("Cor.S", 0, YA, X0, YA); wall("Cor.N", 0, Y1, XT, Y1)
wall("Alcove.W", AX, 0, AX, YA); wall("Alcove.S", AX, 0, X0, 0, "window", (0, 1), bays=1, punched=True)   # hốc tây-nam cũng có 1 ô cửa sổ
box("Alcove.grille", ((AX + X0) / 2 + 0.2, YA - 0.056, 2.6), (1.0, 0.012, 0.14), "grey")   # miệng gió trên mặt nam khối hành lang (thấy trong video)
box("Alcove.cabinet", (AX + 0.3, YA / 2, 0.45), (0.5, YA - 0.5, 0.9), "wood")            # tủ gỗ thấp trong hốc
# cuối hành lang (theo hình vẽ + ảnh của chủ nhà): tường chắn ngang ở y=YM, ngay góc tây có 2 cửa gỗ sẫm —
# cửa B trên tường tây ra thang thoát hiểm (qua buồng đệm rồi cửa C), cửa A trên tường chắn vào phòng kho.
# Phía bắc tường chắn: phòng kho hẹp sát tường tây (x 0–CW), phần còn lại tới tường phòng họp là khối đặc.
CW = XT - 1.0                          # mép đông phòng kho = mặt tây khối đặc
wall("Cor.W1", 0, YA, 0, YM - 1.15); wall("Cor.W2", 0, YM - 0.05, 0, Y1)
place("Exit.doorB", FIRE_DOOR, 0, YM - 0.6, -90)
box("Exit.doorB.top", (0, YM - 0.6, 2.5), (0.1, 1.1, 0.6), "espresso")
box("Exit.lightbox", (0.09, YM - 0.6, 2.32), (0.06, 0.36, 0.14), "exitgreen")
wall("Lobby.S", 1.15, YM, XT, YM)
part("Core.B", "tbox", ((CW + XT) / 2, (YM + Y1) / 2, H / 2), (XT - CW, Y1 - YM, H), "wall", floor_root)   # khối đặc dọc tường phòng họp                                      # tường chắn màu kem, nối liền mặt nam phòng kho
place("Exit.doorA", FIRE_DOOR, 0.6, YM, 180)
box("Exit.doorA.top", (0.6, YM, 2.5), (1.1, 0.1, 0.6), "espresso")
box("Exit.sign", (1.75, YM - 0.056, 1.78), (0.34, 0.008, 0.13), "exitgreen")   # biển mũi tên EXIT chỉ sang trái
box("Exit.alarm", (1.6, YM - 0.058, 1.25), (0.1, 0.012, 0.1), "red"); box("Exit.switch", (1.38, YM - 0.056, 1.25), (0.086, 0.008, 0.086), "white")
box("Exit.mat", (0.75, YM - 0.8, 0.006), (1.3, 1.4, 0.012), "dark")             # thảm sẫm trước hai cửa
box("Cor.panel", (0.06, (8.9 + YM - 1.15) / 2, 1.3), (0.02, YM - 1.15 - 8.9, 2.6), "espresso")   # ốp gỗ sẫm tường tây đoạn gần cửa
ED0, ED1 = 7.1, 8.8                    # hai mép cửa chính (theo video: bảng điều khiển rồi tới ghế bành nằm ngay bắc cửa)
wall("Cor.E1", X0, YA, X0, ED0); wall("Cor.E2", X0, ED1, X0, YM)
part("Entry.top", "tbox", (X0, (ED0 + ED1) / 2, (2.25 + H) / 2), (0.1, ED1 - ED0, H - 2.25), "wall", floor_root)
for i, (ya, yb) in enumerate(((ED0, (ED0 + ED1) / 2), ((ED0 + ED1) / 2, ED1))):   # 2 cánh, kính sẫm màu
    box(f"Entry.leaf{i}.pane", (X0, (ya + yb) / 2, 1.125), (0.02, yb - ya - 0.1, 2.15), "tint")
    for n, (y, z, sy, sz) in enumerate(((ya + 0.04, 1.125, 0.08, 2.25), (yb - 0.04, 1.125, 0.08, 2.25), ((ya + yb) / 2, 0.06, yb - ya, 0.12), ((ya + yb) / 2, 2.21, yb - ya, 0.08))):
        box(f"Entry.leaf{i}.frame{n}", (X0, y, z), (0.06, sy, sz), "slate")
    hy = yb - 0.1 if i == 0 else ya + 0.1
    box(f"Entry.leaf{i}.handle", (X0, hy, 1.05), (0.16, 0.03, 0.14), "metal")
# bảng điều khiển + công tắc trên tường giữa cửa chính và ghế bành; công tắc + ổ điện trên mảng tường nam cửa
box("Entry.panel", (X0 + 0.056, ED1 + 0.5, 1.4), (0.012, 0.36, 0.2), "white"); box("Entry.panel.screen", (X0 + 0.063, ED1 + 0.58, 1.42), (0.004, 0.1, 0.08), "dark")
for i in range(3): box(f"Entry.switch{i}", (X0 + 0.056, ED1 + 0.38 + i * 0.1, 1.2), (0.01, 0.086, 0.086), "white")
box("Entry.switchS", (X0 + 0.056, ED0 - 1.6, 1.25), (0.01, 0.086, 0.086), "white"); place("Entry.outletS", OUTLET, X0 + 0.05, ED0 - 1.6, -90, z=0.32)
# miệng gió điều hoà chạy sát trần trên mảng tường này
for i, (ya, yb) in enumerate(((YA + 0.3, ED0 - 0.1), (ED0 + 0.05, ED1 + 0.2), (ED1 + 0.35, YM - 0.15))):
    box(f"Entry.grille{i}", (X0 + 0.056, (ya + yb) / 2, 2.6), (0.012, yb - ya, 0.14), "grey")
place("Elevator1", ELEVATOR, 0.09, YA + 1.3, 90); place("Elevator2", ELEVATOR, 0.09, YA + 3.7, 90)
# tủ gỗ óc chó cạnh cửa chính (phía hành lang): tủ thấp, hốc có đèn, tủ treo sát trần
box("Cor.cabinet", (X0 - 0.3, ED1 + 0.95, 0.55), (0.5, 0.9, 1.1), "darkwood"); box("Cor.cabinet.back", (X0 - 0.07, ED1 + 0.95, 1.5), (0.04, 0.9, 0.8), "darkwood")
box("Cor.cabinet.top", (X0 - 0.3, ED1 + 0.95, 2.35), (0.5, 0.9, 0.9), "darkwood"); box("Cor.cabinet.led", (X0 - 0.3, ED1 + 0.95, 1.895), (0.4, 0.03, 0.01), "screen")

# 7.4 thang thoát hiểm (x -4–0, y YS–Y1) — theo hình vẽ của chủ nhà: qua cửa B là chiếu nghỉ chạy hết bề ngang ở đầu nam;
# vế ĐI LÊN chạy về bắc dọc tường tây; vế ĐI XUỐNG chạy về bắc dọc tường hành lang, tới đầu bắc rẽ sang tây vài bậc rồi quay về nam ở làn giữa
wall("Stairs.W", -4, YS, -4, Y1); wall("Stairs.S", -4, YS, 0, YS); wall("Stairs.N", -4, Y1, 0, Y1)
RUN, RISE, NS = 0.28, 0.17, 12                                        # mặt bậc, cổ bậc, số bậc mỗi vế
YE, DZ = YL + RUN * NS, RISE * NS                                     # cuối vế thang, chênh cao mỗi vế
SLOPE = math.degrees(math.atan2(DZ, RUN * NS))
def flight(name, x, w, z0, sign, south=False):
    """Vế thang rộng w, tim x: bậc đầu sát chiếu nghỉ (y=YL), sign=+1 đi lên / -1 đi xuống khi tiến về bắc; south=True thì bậc đầu ở đầu bắc, tiến về nam."""
    for i in range(NS):
        y = (YE - RUN * (i + 0.5)) if south else (YL + RUN * (i + 0.5))
        top = z0 + sign * RISE * (i + 1) if sign > 0 else z0 - RISE * (i + 1)
        box(f"{name}.step{i}", (x, y, top - 0.15), (w, RUN, 0.3), "concrete")
# mảng tường đệm nhô ra dọc tường hành lang (dày 0.5 m, từ mép chiếu nghỉ tới tường bắc) → cả cụm thang dịch sang tây
part("Stairs.pad", "tbox", (-0.3, (YL + Y1) / 2, (H - DZ * 2 - RISE * 3 - 0.4) / 2), (0.5, Y1 - YL, H + DZ * 2 + RISE * 3 + 0.4), "wall", floor_root)
flight("Stairs.up", -3.53, 0.82, 0, 1)
box("Stairs.up.landing", (-3.1, (YE + Y1) / 2, DZ - 0.05), (1.7, Y1 - YE, 0.1), "concrete")           # chiếu nghỉ phía trên
flight("Stairs.down", -1.025, 0.95, 0, -1)
box("Stairs.down.landing", (-1.025, (YE + Y1) / 2, -DZ - 0.05), (0.95, Y1 - YE, 0.1), "concrete")        # chiếu nghỉ góc đông-bắc
for i in range(3):                                                                                    # 3 bậc rẽ sang tây
    box(f"Stairs.turn.step{i}", (-1.625 - 0.25 * i, (YE + Y1) / 2, -DZ - RISE * (i + 1) - 0.15), (0.25, Y1 - YE, 0.3), "concrete")
ZM = -DZ - RISE * 3
box("Stairs.mid.landing", (-2.66, (YE + Y1) / 2, ZM - 0.05), (0.82, Y1 - YE, 0.1), "concrete")          # chiếu nghỉ đầu bắc làn giữa
flight("Stairs.mid", -2.66, 0.82, ZM, -1, south=True)
for name, x, zc, rot in (("up", -3.1, DZ / 2, SLOPE), ("down", -1.52, -DZ / 2, -SLOPE), ("mid", -2.23, ZM - DZ / 2, SLOPE)):   # tay vịn theo dốc
    box(f"Stairs.{name}.rail", (x, (YL + YE) / 2, zc + 0.9), (0.04, math.hypot(RUN * NS, DZ), 0.04), "grey").rotation_euler = (math.radians(rot), 0, 0)
for i, z in enumerate((0.45, 0.9)):                                                                   # lan can mép chiếu nghỉ, chỗ nhìn xuống giếng thang
    box(f"Stairs.guard{i}", (-2.3, YL, z), (1.6, 0.04, 0.04), "grey")
for i, x in enumerate((-3.1, -2.3, -1.5)):
    box(f"Stairs.guard.post{i}", (x, YL, 0.45), (0.04, 0.04, 0.9), "grey")

# vách kính ngăn khu làm việc với dải phòng: cửa phòng họp ngay tây góc XM, pantry mở hoàn toàn (cửa lùa)
DW = 1.4                              # bề rộng cửa phòng họp (1 cánh)
wall("Glass.W", X0, YM, XM - 0.1 - DW, YM, "glass", bays=2)   # 2 ô kính + cửa
# pantry không có vách kính: cả đoạn XM→X1 là cửa lùa xanh dương, hai cụm cánh xếp ở hai đầu, kéo vào giữa để đóng
PART_OPEN = 1.0                       # 1 = mở hết (cánh xếp chồng ở hai đầu), 0 = đóng kín
box("Part.header", ((XM + X1) / 2, YM, H - 0.04), (X1 - XM, 0.1, 0.08), "dark")
# dầm hộp thạch cao phía trên vách kính phòng họp + ray cửa lùa pantry (theo video: kính chỉ cao ~2.4 m, phía trên là hộp trắng có miệng gió điều hoà)
part("Bulkhead", "tbox", ((X0 + X1) / 2, YM, H - 0.2), (X1 - X0, 0.16, 0.4), "wall", floor_root)
for i in range(5):
    gl = (X1 - X0 - 0.6) / 5
    box(f"Bulkhead.grille{i}", (X0 + 0.3 + gl * (i + 0.5), YM - 0.086, H - 0.2), (gl - 0.25, 0.012, 0.14), "grey")
box("Part.track", ((XM + X1) / 2, YM, 0.003), (X1 - XM, 0.05, 0.006), "dark")
PN = round((X1 - XM - 0.16) / 2 / 0.5); PW = (X1 - XM - 0.16) / 2 / PN   # số cánh mỗi bên, bề rộng cánh ~0.5 m
for side, x_end, sgn in (("W", XM + 0.08, 1), ("E", X1, -1)):
    for i in range(PN):
        box(f"Part.{side}{i}", (x_end + sgn * PW * (0.5 + i * (1 - PART_OPEN)), YM + (i - (PN - 1) / 2) * 0.014 * PART_OPEN, (H - 0.08) / 2),
            (PW, 0.012, H - 0.09), "navy")
# cửa phòng họp: trên vách kính phía sofa, sát góc đông; cánh kính khung đen đang mở vào trong, bản lề phía đông
HD, LW = H - 0.08, DW                 # cánh cao tới đố ngang trên cùng; cửa 1 cánh, đang mở vào trong, bản lề phía cột góc
for side, dx in (("E", XM - 0.12),):
    box(f"Meet.door{side}.pane", (dx, YM + LW / 2, HD / 2), (0.02, LW - 0.04, HD - 0.04), "glass")
    for n, (y, z, sy, sz) in enumerate(((YM + 0.05, HD / 2, 0.06, HD), (YM + LW - 0.05, HD / 2, 0.06, HD), (YM + LW / 2, 0.03, LW, 0.06), (YM + LW / 2, HD - 0.03, LW, 0.06))):
        box(f"Meet.door{side}.frame{n}", (dx, y, z), (0.045, sy, sz), "dark")
    box(f"Meet.door{side}.handle", (dx + (-0.05 if side == "E" else 0.05), YM + LW - 0.12, 1.0), (0.06, 0.12, 0.03), "metal")

# 7.6 phòng họp (x 2.6–10.1, y 12–16.5) — dựng theo ảnh chụp trong phòng
# kính phía nam (ra sofa) và phía đông (sang pantry, cửa ở đầu nam); TV + tủ góc ở tường hành lang; cửa sổ phía bắc
wall("Meet.E", XM, YM, XM, Y1, "glass")
box("Meet.corner", (XM, YM, H / 2), (0.16, 0.16, H), "dark")
# theo hình vẽ của chủ nhà: phòng họp ăn sâu 1.4 m sang dải hành lang (tường sau TV ở x=XT);
# mảng tường góc tây-nam (chỗ ray kệ + thanh treo đồ) phẳng với tường hành lang, phía sau nó là khối đặc
part("Core.A", "tbox", ((XT + X0) / 2, YM + 0.65, H / 2), (X0 - XT, 1.3, H), "wall", floor_root)   # khối đặc ở góc tây-nam phòng họp (trước đây dựng nhầm thành phòng kho)
wall("Meet.W", XT, YM + 1.3, XT, Y1)
box("Meet.floor", ((XT + X0) / 2, (YM + 1.3 + Y1) / 2, -0.05), (X0 - XT, Y1 - YM - 1.3, 0.1), "floor"); quad("Meet.floor.planks", XT, YM + 1.3, X0, Y1, 0.004, "planks")
for i, y in enumerate((YM + 0.3, YM + 1.0)):
    box(f"Meet.rail{i}", (X0 + 0.07, y, 1.3), (0.02, 0.04, 2.2), "white")
for i, z in enumerate((0.45, 0.95, 1.75)):
    box(f"Meet.shelf{i}", (X0 + 0.19, YM + 0.65, z), (0.25, 0.9, 0.03), "wood")
box("Meet.rod", (X0 + 0.23, YM + 0.65, 1.66), (0.02, 0.85, 0.02), "metal")
place("Meet.table", MEETING_TABLE, XT + 3.2, 14.6, 90)   # đầu bàn cách tường TV ~1.7 m, cách vách kính pantry ~1.5 m
for i, x in enumerate((XT + 2.2, XT + 3.2, XT + 4.2)):
    place(f"Meet.chairS{i}", MEET_CHAIR, x, 13.7, 0); place(f"Meet.chairN{i}", MEET_CHAIR, x, 15.5, 180)
place("Meet.tv", TV, XT + 0.5, 14.5, -90)
place("Meet.outlet", OUTLET, XT + 0.05, 13.45, -90, z=1.15)                   # ổ điện trên tường, bên trái TV
box("Meet.tv.cable", (XT + 0.062, 13.925, 0.825), (0.008, 1.15, 0.008), "black").rotation_euler = (math.radians(-34.4), 0, 0)
box("Meet.cabinet.seam", (XT + 0.556, 15.9, 0.4), (0.004, 0.008, 0.68), "darkwood"); box("Meet.cabinet.toe", (XT + 0.557, 15.9, 0.03), (0.004, 0.8, 0.06), "dark")
box("Meet.cabinet", (XT + 0.33, 15.9, 0.375), (0.45, 0.8, 0.75), "wood")       # tủ góc + tranh + đèn
box("Meet.frame", (XT + 0.3, 15.95, 0.93), (0.03, 0.34, 0.34), "white")
box("Meet.art", (XT + 0.32, 15.95, 0.93), (0.01, 0.24, 0.24), "green")
part("Meet.lamp", "cyl", (XT + 0.38, 15.6, 0.83), (0.05, 0.05, 0.16), "yellow", floor_root)

# pantry (x XM–X1, y 12–16.5) — dựng theo ảnh: bếp chạy dọc tường đông, quầy bar bắc–nam tựa trụ tường bắc, bàn ăn phía tây quầy
part("Pantry.pier", "tbox", (XB, Y1 - 0.15, H / 2), (1.1, 0.3, H), "wall", floor_root)              # trụ tường nhô ra, treo tranh
box("Pantry.painting", (XB, Y1 - 0.31, 1.75), (0.62, 0.03, 0.97), "black")
box("Pantry.painting.mat", (XB, Y1 - 0.327, 1.75), (0.54, 0.006, 0.89), "white")
box("Pantry.painting.art", (XB, Y1 - 0.331, 1.75), (0.42, 0.006, 0.77), "yellow")
place("Pantry.outlet", OUTLET, XB - 0.47, Y1 - 0.3, 180, z=0.4)                # ổ điện thấp trên trụ, cạnh đầu quầy
for i in range(2): place(f"Kit.outlet{i}", OUTLET, X1 - 0.07, Y1 - 0.8 + i * 0.1, 90, z=1.05)   # ổ đôi trên ốp tường bếp
place("Pantry.bar", BAR, XB, Y1 - 1.65)                                        # y 13.5–16.2
for i in range(3):
    place(f"Pantry.stoolW{i}", STOOL, XB - 0.68, 14.0 + i * 0.75, -90); place(f"Pantry.stoolE{i}", STOOL, XB + 0.68, 14.0 + i * 0.75, 90)
place("Pantry.vase", VASE, XB, Y1 - 0.55, z=1.05)
# thùng rác đạp chân ở góc giữa trụ treo tranh và tường bắc: thân hộp chữ nhật dài ngang màu bạc, nắp + đế đen, bàn đạp phía trước, túi rác xanh lộ mép dưới nắp
place("Pantry.bin", [("box", (0, 0, 0.025), (0.5, 0.32, 0.05), "black"), ("box", (0, 0, 0.34), (0.48, 0.3, 0.58), "steel"),
                     ("box", (0, 0, 0.627), (0.495, 0.315, 0.022), "blue"), ("box", (0, 0, 0.657), (0.5, 0.32, 0.04), "black"),
                     ("box", (0.1, 0.158, 0.585), (0.13, 0.01, 0.07), "blue", (6, 0, 0)), ("box", (-0.15, 0.158, 0.595), (0.09, 0.01, 0.05), "blue", (6, 0, 0)),
                     ("box", (0, 0.195, 0.022), (0.1, 0.09, 0.014), "black", (12, 0, 0))], XB + 0.83, Y1 - 0.23, 180)
part("Pantry.speaker", "cyl", (XB - 0.22, Y1 - 0.45, 1.13), (0.12, 0.12, 0.16), "black", floor_root)
# bếp tường đông, từ nam lên bắc: tủ lạnh | máy rửa bát | tủ 2 cánh dưới bồn rửa | tủ ngăn kéo
KX = X1 - 0.32                                                                 # tim khối bếp (sâu 0.64)
box("Kit.fridge", (X1 - 0.37, YM + 0.5, 0.875), (0.72, 0.7, 1.75), "black")
box("Kit.fridge.split", (X1 - 0.733, YM + 0.5, 0.62), (0.006, 0.7, 0.015), "metal")
box("Kit.fridge.water", (X1 - 0.733, YM + 0.45, 1.2), (0.006, 0.2, 0.3), "dark")
box("Kit.fridge.box", (X1 - 0.35, YM + 0.5, 1.8), (0.4, 0.5, 0.1), "wood")
box("Kit.dishwasher", (KX, YM + 1.2, 0.42), (0.6, 0.58, 0.84), "steel")
box("Kit.dishwasher.panel", (KX - 0.302, YM + 1.2, 0.79), (0.006, 0.58, 0.08), "black")
box("Kit.base", (KX + 0.02, (YM + 1.5 + Y1) / 2, 0.47), (0.6, Y1 - YM - 1.5, 0.78), "wood")
box("Kit.toe", (KX + 0.05, (YM + 1.5 + Y1) / 2, 0.04), (0.5, Y1 - YM - 1.5, 0.08), "dark")
for i, y in enumerate((YM + 2.05, YM + 2.6)):                                  # khe cánh tủ dưới bồn rửa
    box(f"Kit.seamV{i}", (KX - 0.282, y, 0.47), (0.006, 0.012, 0.78), "darkwood")
for i, z in enumerate((0.34, 0.6)):                                            # khe 3 ngăn kéo
    box(f"Kit.seamH{i}", (KX - 0.282, (YM + 2.6 + Y1) / 2, z), (0.006, Y1 - YM - 2.6, 0.012), "darkwood")
box("Kit.counter", (KX, (YM + 0.88 + Y1) / 2, 0.88), (0.64, Y1 - YM - 0.88, 0.04), "black")
box("Kit.splash", (X1 - 0.06, (YM + 0.88 + Y1) / 2, 1.2), (0.02, Y1 - YM - 0.88, 0.6), "dark")
box("Kit.sink", (KX - 0.03, YM + 2.15, 0.902), (0.4, 0.6, 0.008), "metal")
part("Kit.faucet", "cyl", (X1 - 0.15, YM + 2.15, 1.1), (0.03, 0.03, 0.4), "metal", floor_root)
box("Kit.faucet.arm", (X1 - 0.24, YM + 2.15, 1.3), (0.2, 0.03, 0.03), "metal")
box("Kit.rack", (X1 - 0.19, YM + 2.1, 1.62), (0.26, 1.0, 0.3), "black")        # kệ đen úp bát trên bồn rửa
box("Kit.rack.shelf", (X1 - 0.19, YM + 2.1, 1.38), (0.26, 1.0, 0.02), "black")
box("Kit.shelf", (X1 - 0.15, Y1 - 0.6, 1.5), (0.18, 0.6, 0.02), "black")       # kệ ly phía bắc
box("Kit.oven", (KX, YM + 1.25, 1.07), (0.42, 0.5, 0.34), "steel")
box("Kit.oven.door", (KX - 0.213, YM + 1.25, 1.07), (0.006, 0.4, 0.24), "black")
box("Kit.coffee", (KX + 0.08, Y1 - 0.45, 1.05), (0.25, 0.3, 0.3), "black")
# bàn ăn dài bắc–nam phía tây quầy bar: 4 ghế mỗi bên — phía tây 4 ghế vỏ trắng, phía đông 3 ghế trắng + ghế gỗ đệm xanh ở đầu bắc
TX = XB - 2.35
place("Pantry.table", DINING_TABLE, TX, 14.4)
for i in range(4):
    y = 14.4 + (i - 1.5) * 0.62
    place(f"Pantry.chairW{i}", PANTRY_CHAIR, TX - 0.65, y, -90)
    place(f"Pantry.chairE{i}", WOOD_CHAIR if i == 3 else PANTRY_CHAIR, TX + 0.65, y, 90)

# khu làm việc (x X0–X1, y 0–12) — theo bản vẽ layout của chủ nhà: 7 bàn 4 chỗ
# shortcut: bản vẽ không ghi kích thước nên vị trí lấy theo tỉ lệ hình, bàn giả định 2.36 × 1.2 m
for i in range(3): work_table(f"Desk.S{i}", X1 - 0.75 - TL * (i + 0.5), 1.9)            # hàng nam: 3 bàn nối liền
for i in range(2): work_table(f"Desk.M{i}", X1 - 2.05 - TL * (i + 0.5), 5.2)            # hàng giữa: 2 bàn nối liền, đầu đông có tủ gỗ
work_table("Desk.N", X1 - 4.3, 8.3)
box("Desk.pc", (X1 - 2.05 - TL * 1.5 - 0.95, 5.2, 1.0), (0.24, 0.48, 0.5), "white"); box("Desk.pc.glass", (X1 - 2.05 - TL * 1.5 - 0.95, 5.2 - 0.242, 1.0), (0.2, 0.004, 0.44), "scr_hi")   # thùng máy trắng mặt kính đặt trên bàn (thấy trong video)                                                      # hàng bắc: 1 bàn riêng, phía đông là kệ sách
work_table("Desk.W", X0 + 0.35, 2.05, 90)                                                # bàn xoay dọc ở góc tây-nam, cạnh hốc tủ gỗ
place("Bookshelf", BOOKSHELF, X1 - 1.75, YM - 3.3, 90)                # cột xanh bọc kệ gỗ, sát tường đông, ngay nam bảng ghim; cạnh nó là ô cửa sổ có chậu cây
part("Plant.pot", "cyl", (X1 - 0.4, YM - 5.0, 0.2), (0.3, 0.3, 0.4), "white", floor_root)
for i, (dx, dy, z) in enumerate(((0, 0, 0.75), (0.12, 0.1, 1.0), (-0.1, 0.12, 1.2), (0.05, -0.12, 1.35))):
    part(f"Plant.leaf{i}", "rbox", (X1 - 0.4 + dx, YM - 5.0 + dy, z), (0.3, 0.3, 0.3), "c_green" if "c_green" in M else "green", floor_root)
box("Cabinet.E", (X1 - 0.3, 2.35, 0.55), (0.45, 2.7, 1.1), "wood")     # tủ gỗ dài dọc tường đông, đoạn phía nam
box("Cabinet.E2", (X1 - 1.8, 5.3, 0.55), (0.45, 2.2, 1.1), "wood")    # tủ gỗ ngắn ở đầu đông hàng bàn giữa
for i, y in enumerate((1.4, 3.2)): box(f"Cabinet.E.speaker{i}", (X1 - 0.3, y, 1.2), (0.14, 0.14, 0.2), "dark")
# trần bê tông lộ: ray đèn rọi đen + ống chữa cháy đỏ
for i, y in enumerate((2.6, 6.2, 9.6)):
    box(f"Track{i}", ((X0 + X1) / 2, y, HC - 0.12), (X1 - X0 - 1.5, 0.035, 0.035), "black")
    for j in range(5):
        part(f"Track{i}.spot{j}", "cyl", (X0 + 1.6 + j * (X1 - X0 - 3.2) / 4, y, HC - 0.22), (0.07, 0.07, 0.16), "black", floor_root).rotation_euler = (math.radians(25), 0, 0)
box("FirePipe.EW", ((X0 + X1) / 2, 4.4, HC - 0.08), (X1 - X0 - 0.2, 0.05, 0.05), "firered"); box("FirePipe.NS", (X0 + 3.2, YM / 2, HC - 0.08), (0.05, YM - 0.2, 0.05), "firered")
# theo ảnh: 2 ghế bành tựa tường hành lang sát góc vách kính, bàn kính nhỏ ở giữa, ghế thư giãn trước vách kính
place("Lounge.arm1", armchair(1), X0 + 0.5, 10.3, -90); place("Lounge.arm2", armchair(-1), X0 + 0.5, 11.47, -90)
place("Lounge.sidetable", SIDE_TABLE, X0 + 0.3, 10.88)
part("Lounge.cushion", "rbox", (X0 + 0.52, 11.25, 0.62), (0.14, 0.42, 0.42), "velvet", floor_root).rotation_euler = (0, math.radians(-15), 0)
place("Lounge.wingchair", WING_CHAIR, 6.2, 11.3, 165)

# ================= cảnh thành phố ngoài cửa sổ =================
# shortcut: khối nhà sinh ngẫu nhiên cho có cảm giác nhìn từ tầng 7 (nhà thấp san sát, sân bay + nhà vòm phía bắc như trong ảnh), không phải bản đồ thật
GZ = -24.0                              # cao độ mặt đất so với sàn tầng 7
for k, c in dict(c_ground=(0.2, 0.2, 0.2), c_field=(0.33, 0.42, 0.24), c_runway=(0.32, 0.32, 0.33), c_white=(0.8, 0.8, 0.77), c_cream=(0.72, 0.62, 0.45),
                 c_grey=(0.5, 0.5, 0.5), c_blue=(0.3, 0.45, 0.62), c_red=(0.5, 0.17, 0.1), c_roof=(0.36, 0.37, 0.39), c_green=(0.16, 0.3, 0.13)).items():
    M[k] = mat(k, c, rough=0.9)
city = {}
def cb(m, loc, size): city.setdefault(m, []).append((loc, size))
CX, CY = 9, 8
rnd = random.Random(11)
cb("c_ground", (CX, CY, GZ - 0.5), (1600, 1600, 1))
cb("c_field", (CX, 520, GZ + 0.05), (1600, 560, 0.1))                           # bãi cỏ sân bay phía bắc
cb("c_runway", (CX, 560, GZ + 0.12), (1500, 45, 0.1)); cb("c_runway", (CX, 400, GZ + 0.12), (1100, 22, 0.1))
cb("c_blue", (CX + 60, 269.5, GZ + 9), (84, 1, 18))                             # mặt trước xanh của nhà vòm
for dx, w in ((-90, 70), (190, 110)): cb("c_white", (CX + dx, 275, GZ + 5), (w, 30, 10))   # nhà ga / kho thấp cạnh nhà vòm
cb("c_grey", (X1 / 2, Y1 / 2, (GZ - 0.13) / 2), (X1, Y1, -0.13 - GZ))            # thân tòa IKIGAI bên dưới tầng 7
SB = -DZ * 2 - RISE * 3 - 0.4                                                    # đáy phần giếng thang để hở (đủ cho 2 vế đi xuống)
cb("c_grey", (-2, (YS + Y1) / 2, (GZ + SB) / 2), (4, Y1 - YS, SB - GZ))          # lõi thang bên dưới
cb("c_grey", (-4, (YS + Y1) / 2, SB / 2), (0.1, Y1 - YS, -SB)); cb("c_grey", (-2, YS, SB / 2), (4, 0.1, -SB)); cb("c_grey", (-2, Y1, SB / 2), (4, 0.1, -SB))   # vách giếng thang dưới sàn
for i in range(-26, 27):
    for j in range(-26, 20):
        x, y = CX + i * 13 + rnd.uniform(-1.5, 1.5), CY + j * 13 + rnd.uniform(-1.5, 1.5)
        if y > 225 or (-14 < x < X1 + 12 and -10 < y < Y1 + 10) or rnd.random() < 0.1: continue
        if rnd.random() < 0.06:                                                  # khoảng cây xanh
            cb("c_green", (x, y, GZ + 3), (9, 9, 6)); continue
        near = math.hypot(x - CX, y - CY) < 45
        h = rnd.uniform(16, 20 if near else 34) if rnd.random() < 0.1 else rnd.uniform(7, 15)
        w, d = rnd.uniform(7, 11), rnd.uniform(7, 11)
        cb(rnd.choice(("c_white", "c_white", "c_cream", "c_grey", "c_blue")), (x, y, GZ + h / 2), (w, d, h))
        cb(rnd.choice(("c_red", "c_red", "c_roof", "c_roof", "c_white")), (x, y, GZ + h + 0.2), (w + 0.5, d + 0.5, 0.4))
city_col = bpy.data.collections.new("City"); scene.collection.children.link(city_col)   # collection riêng để tắt/bật trong Blender
for m, lst in city.items():
    me = bpy.data.meshes.new("City." + m); bm = bmesh.new()
    for loc, size in lst:
        bmesh.ops.create_cube(bm, size=1, matrix=mathutils.Matrix.Translation(loc) @ mathutils.Matrix.Diagonal((*size, 1)))
    bm.to_mesh(me); bm.free(); me.materials.append(M[m])
    city_col.objects.link(bpy.data.objects.new("City." + m, me))
hangar = bpy.data.objects.new("City.hangar", mesh("cyl", "c_white"))            # nhà vòm sân bay: nửa trụ nằm ngang
hangar.location, hangar.scale, hangar.rotation_euler = (CX + 60, 305, GZ), (100, 50, 70), (math.radians(90), 0, 0)
city_col.objects.link(hangar)

# ================= trần + ánh sáng =================
# trần thạch cao trắng cho dải phòng phía bắc và hành lang, trần bê tông cho khu làm việc; hiện dạng khung dây trong viewport Blender cho khỏi che
# khu làm việc + hốc tây-nam: trần cao HC, nên quanh chu vi nối thêm một băng tường từ H lên HC
for i, (xa, ya, xb, yb) in enumerate(((AX, 0, X1, 0), (X1, 0, X1, YM), (X0, YM, X1, YM), (X0, YA, X0, YM), (AX, YA, X0, YA), (AX, 0, AX, YA))):
    part(f"Upper{i}", "tbox", ((xa + xb) / 2, (ya + yb) / 2, (H + HC) / 2), (abs(xb - xa) or 0.1, abs(yb - ya) or 0.1, HC - H), "wall", floor_root)
for o in (quad("Ceil.north", XT, YM, X1, Y1, H, "ceil", up=False), quad("Ceil.office", X0, 0, X1, YM, HC, "ceilc", up=False),
          quad("Ceil.alcove", AX, 0, X0, YA, HC, "ceilc", up=False),
          quad("Ceil.corridor", 0, YA, X0, YM, H, "ceil", up=False), quad("Ceil.corridorN", 0, YM, XT, Y1, H, "ceil", up=False)):
    o.display_type = "WIRE"
# ánh sáng cho render trong Blender (không xuất sang GLB): trời sáng đục + nắng chiếu xiên từ phía cửa sổ bắc
world = bpy.data.worlds.new("Sky"); world.use_nodes = True; scene.world = world
world.node_tree.nodes["Background"].inputs[0].default_value = (0.82, 0.9, 1.0, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN")); sun.data.energy = 3.0; sun.data.angle = math.radians(3)
sun.rotation_euler = mathutils.Vector((-0.25, -0.7, -0.67)).to_track_quat("-Z", "Y").to_euler()
sun.location = (9, 20, 12); scene.collection.objects.link(sun)

# ================= xuất =================
assert len(scene.objects) > 300, len(scene.objects)
for n in ("Glass.W.pane", "Part.W0", "Part.E0", "D2.exit", "Kit.fridge", "Meet.E.pane", "Win.N.meet.pane"):
    assert n in bpy.data.objects, n
os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
glb = os.path.join(ROOT, "assets", "floor7.glb")
bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "blender", "floor7.blend"))
assert os.path.getsize(glb) > 10000
print("OK objects:", len(scene.objects), "glb bytes:", os.path.getsize(glb))
