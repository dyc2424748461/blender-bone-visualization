bl_info = {
    "name": "骨骼可视化工具",
    "author": "yc with Gemini，claude 3.7",
    "version": (1, 3, 1),
    "blender": (3, 0, 0),
    "location": "工具栏 > MyTools > 骨骼可视化",
    "description": "为选定的骨架创建和删除可渲染的骨骼可视化对象，并提供自定义选项，支持多选骨架。",
    "category": "动画",
}

import bpy
import bmesh
from mathutils import Vector, Matrix
import math

def create_bone_mesh(armature_obj, scale_factor=0.1, bone_shape='CONE', bone_color=(0.8, 0.8, 0.0)):
    if armature_obj.type != 'ARMATURE':
        print(f"对象 '{armature_obj.name}' 不是骨架对象")
        return

    # 存储当前选择和活动对象
    original_selection = bpy.context.selected_objects.copy()
    original_active = bpy.context.active_object
    original_mode = bpy.context.mode

    # 确保对象模式
    if original_mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # 创建或获取骨骼可视化集合 (基于当前骨架对象名称)
    collection_name = f"{armature_obj.name}_BoneVisualization"
    if collection_name not in bpy.data.collections:
        vis_collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(vis_collection)
    else:
        vis_collection = bpy.data.collections[collection_name]

    # 取消选择所有对象
    bpy.ops.object.select_all(action='DESELECT')

    # 选择和激活骨架对象
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj

    # 进入姿态模式以访问姿态骨骼
    bpy.ops.object.mode_set(mode='POSE')
    pose_bones = armature_obj.pose.bones

    # 收集姿态骨骼数据
    bone_data = []
    for pose_bone in pose_bones:
        # 只处理非隐藏的骨骼
        if not pose_bone.bone.hide:
            bone_data.append({
                'name': pose_bone.name,
                'head': pose_bone.head.copy(),
                'tail': pose_bone.tail.copy(),
                'matrix': pose_bone.matrix.copy(),
                'length': pose_bone.length,
                'parent': pose_bone.parent.name if pose_bone.parent else None
            })

    # 返回对象模式
    bpy.ops.object.mode_set(mode='OBJECT')

    # 为每个骨骼创建可视化
    for data in bone_data:
        bone_vec = data['tail'] - data['head']
        bone_length = bone_vec.length
        bone_radius = bone_length * scale_factor

        mesh = bpy.data.meshes.new(name=f"{armature_obj.name}_{data['name']}_vis_mesh")
        bone_obj = bpy.data.objects.new(name=f"{armature_obj.name}_{data['name']}_vis", object_data=mesh)

        vis_collection.objects.link(bone_obj)

        bm = bmesh.new()

        if bone_shape == 'CONE':
            segments = 8
            bottom_verts = []
            for i in range(segments):
                angle = 2 * math.pi * i / segments
                x = bone_radius * math.cos(angle)
                z = bone_radius * math.sin(angle)
                y = 0
                bottom_verts.append(bm.verts.new((x, y, z)))
            tip_vert = bm.verts.new((0, bone_length, 0))
            if len(bottom_verts) >= 3:
                bm.faces.new(bottom_verts)
            for i in range(segments):
                v1 = bottom_verts[i]
                v2 = bottom_verts[(i + 1) % segments]
                bm.faces.new((v1, v2, tip_vert))
        elif bone_shape == 'BOX':
            width = bone_radius * 2
            bm.verts.new((-width/2, 0, -width/2))
            bm.verts.new((width/2, 0, -width/2))
            bm.verts.new((width/2, 0, width/2))
            bm.verts.new((-width/2, 0, width/2))
            bm.verts.new((-width/2, bone_length, -width/2))
            bm.verts.new((width/2, bone_length, -width/2))
            bm.verts.new((width/2, bone_length, width/2))
            bm.verts.new((-width/2, bone_length, width/2))
            faces = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (0, 3, 2, 1), (4, 5, 6, 7)]
            for face in faces:
                bm.faces.new([bm.verts[i] for i in face])
        elif bone_shape == 'CYLINDER':
            segments = 12
            bottom_verts = []
            top_verts = []
            for i in range(segments):
                angle = 2 * math.pi * i / segments
                x = bone_radius * math.cos(angle)
                z = bone_radius * math.sin(angle)
                bottom_verts.append(bm.verts.new((x, 0, z)))
                top_verts.append(bm.verts.new((x, bone_length, z)))
            if len(bottom_verts) >= 3:
                bm.faces.new(bottom_verts)
                bm.faces.new(top_verts)
            for i in range(segments):
                v1 = bottom_verts[i]
                v2 = bottom_verts[(i + 1) % segments]
                v3 = top_verts[i]
                v4 = top_verts[(i + 1) % segments]
                bm.faces.new((v1, v2, v4, v3))

        bm.to_mesh(mesh)
        bm.free()

        mat = bpy.data.materials.get("BoneVisMaterial")
        if not mat:
            mat = bpy.data.materials.new(name="BoneVisMaterial")
            mat.diffuse_color = bone_color + (1.0,)

        if bone_obj.data.materials:
            bone_obj.data.materials[0] = mat
        else:
            bone_obj.data.materials.append(mat)

        bone_obj.matrix_world = armature_obj.matrix_world @ data['matrix']

        copy_loc = bone_obj.constraints.new('COPY_LOCATION')
        copy_loc.target = armature_obj
        copy_loc.subtarget = data['name']

        copy_rot = bone_obj.constraints.new('COPY_ROTATION')
        copy_rot.target = armature_obj
        copy_rot.subtarget = data['name']

    # 恢复原始选择
    bpy.ops.object.select_all(action='DESELECT')
    for obj in original_selection:
        obj.select_set(True)
    if original_active:
        bpy.context.view_layer.objects.active = original_active

    # 恢复原始模式
    if original_mode != 'OBJECT':
        bpy.ops.object.mode_set(mode=original_mode)

    print(f"骨骼 '{armature_obj.name}' 的可视化创建完成！")

def remove_bone_visualization(armature_obj=None):
    if armature_obj:
        collection_name = f"{armature_obj.name}_BoneVisualization"
        if collection_name in bpy.data.collections:
            collection = bpy.data.collections[collection_name]
            # 遍历集合中的对象并删除
            for obj in list(collection.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            # 删除集合
            bpy.data.collections.remove(collection)
            print(f"骨骼 '{armature_obj.name}' 的可视化已删除！")
        else:
            print(f"未找到骨骼 '{armature_obj.name}' 的可视化集合！")
    else:
        # 删除所有骨骼可视化集合
        collections_to_remove = [col for col in bpy.data.collections if col.name.endswith("_BoneVisualization")]
        for collection in collections_to_remove:
            # 遍历集合中的对象并删除
            for obj in list(collection.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            # 删除集合
            bpy.data.collections.remove(collection)
        print("所有骨骼可视化已删除！")

    # 移除不再使用的材质
    if "BoneVisMaterial" in bpy.data.materials:
        mat = bpy.data.materials["BoneVisMaterial"]
        if not mat.users:
            bpy.data.materials.remove(mat)

class BONE_OT_create_visualization(bpy.types.Operator):
    """为当前选择的骨架创建可渲染的骨骼可视化"""
    bl_idname = "armature.create_bone_visualization"
    bl_label = "创建骨骼可视化"
    bl_options = {'REGISTER', 'UNDO'}

    scale_factor: bpy.props.FloatProperty(
        name="半径比例",
        description="骨骼可视化半径相对于骨骼长度的比例",
        default=0.1,
        min=0.01,
        max=1.0
    )

    bone_shape: bpy.props.EnumProperty(
        name="形状",
        description="骨骼可视化的形状",
        items=[
            ('CONE', "圆锥", "使用圆锥体表示骨骼"),
            ('BOX', "方块", "使用方块表示骨骼"),
            ('CYLINDER', "圆柱", "使用圆柱体表示骨骼"),
        ],
        default='CONE'
    )

    bone_color: bpy.props.FloatVectorProperty(
        name="颜色",
        subtype='COLOR',
        default=(1.0, 0.5, 0.0),
        min=0.0,
        max=1.0,
        description="骨骼可视化的颜色",
        size=3,
    )

    def execute(self, context):
        selected_armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']

        if not selected_armatures:
            self.report({'ERROR'}, "请先选择一个或多个骨架对象")
            return {'CANCELLED'}

        for armature_obj in selected_armatures:
            create_bone_mesh(
                armature_obj,
                scale_factor=self.scale_factor,
                bone_shape=self.bone_shape,
                bone_color=self.bone_color[:]
            )
        return {'FINISHED'}

class BONE_OT_remove_visualization(bpy.types.Operator):
    """删除所有骨骼可视化对象"""
    bl_idname = "armature.remove_all_bone_visualization"
    bl_label = "删除所有骨骼可视化"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        remove_bone_visualization()
        return {'FINISHED'}

class BONE_OT_remove_selected_visualization(bpy.types.Operator):
    """删除当前选择的骨架的所有骨骼可视化对象"""
    bl_idname = "armature.remove_selected_bone_visualization"
    bl_label = "删除选定骨骼可视化"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']

        if not selected_armatures:
            self.report({'ERROR'}, "请先选择一个或多个骨架对象")
            return {'CANCELLED'}

        for armature_obj in selected_armatures:
            remove_bone_visualization(armature_obj=armature_obj)
        return {'FINISHED'}

class BONE_PT_visualization_panel(bpy.types.Panel):
    """骨骼可视化工具面板"""
    bl_label = "骨骼可视化"
    bl_idname = "BONE_PT_visualization"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tools'

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        op = row.operator("armature.create_bone_visualization")

        layout.prop(op, "scale_factor")
        layout.prop(op, "bone_shape")
        layout.prop(op, "bone_color", text="")

        layout.separator()

        row = layout.row()
        row.operator("armature.remove_all_bone_visualization")
        row = layout.row()
        row.operator("armature.remove_selected_bone_visualization")

# 注册
classes = (
    BONE_OT_create_visualization,
    BONE_OT_remove_visualization,
    BONE_OT_remove_selected_visualization,
    BONE_PT_visualization_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
