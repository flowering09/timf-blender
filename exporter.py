import bpy
import os 
import struct

from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty



class ExportWiiMesh(Operator, ExportHelper):

    bl_idname = "export_mesh.wii_h"
    bl_label = "Export Terrence Engine Mesh"

    filename_ext = ".timf"

    filter_glob: StringProperty(
        default="*.timf",
        options={'HIDDEN'}
    )


    export_animation: BoolProperty(
        name="Export Animation",
        description="Export every frame as a mesh",
        default=False
    )


    def draw(self, context):

        layout = self.layout

        layout.prop(
            self,
            "export_animation"
        )


    def execute(self, context):

        base = os.path.splitext(self.filepath)[0]

        if self.export_animation:
            self.filepath = base + ".tiaf"
        else:
            self.filepath = base + ".timf"

        objects = [
            obj
            for obj in context.selected_objects
            if obj.type == "MESH"
        ]


        if len(objects) == 0:

            self.report(
                {'ERROR'},
                "No meshes selected"
            )

            return {'CANCELLED'}



        if self.export_animation:

            if len(objects) == 0:

                self.report(
                    {'ERROR'},
                    "No meshes selected"
                )

                return {'CANCELLED'}


            export_animation(
                objects,
                self.filepath
            )


        else:

            export_mesh(
                objects,
                self.filepath
            )


        self.report(
            {'INFO'},
            "Exported Wii asset"
        )


        return {'FINISHED'}





def clean_name(name):

    name = name.lower()

    return "".join(
        c if c.isalnum() else "_"
        for c in name
    )

def get_emission_color(material):

    if material is None:
        return (1.0, 1.0, 1.0, 1.0)


    if not material.use_nodes:
        return (1.0, 1.0, 1.0, 1.0)


    nodes = material.node_tree.nodes


    #
    # Separate Emission node
    #

    emission_node = nodes.get(
        "Emission"
    )

    if emission_node:

        return emission_node.inputs[
            0
        ].default_value



    #
    # Principled fallback
    #

    bsdf = nodes.get(
        "Principled BSDF"
    )


    if bsdf:

        emission = bsdf.inputs.get(
            "Emission Color"
        )


        if emission is None:

            emission = bsdf.inputs.get(
                "Emission"
            )


        if emission:

            return emission.default_value



    return (
        1.0,
        1.0,
        1.0,
        1.0
    )

def collect_mesh_data(obj, source_mesh=None):

    if source_mesh is None:

        mesh = obj.data

    else:

        mesh = source_mesh



    mesh.calc_loop_triangles()


    vertices = []
    indices = []

    vertex_lookup = {}



    #
    # Materials
    #

    materials = []


    for mat in mesh.materials:

        materials.append(
            get_emission_color(mat)
        )



    for tri in mesh.loop_triangles:


        if tri.material_index < len(materials):

            emission = materials[
                tri.material_index
            ]

        else:

            emission = (
                1.0,
                1.0,
                1.0,
                1.0
            )



        color = (

            int(emission[0] * 255),
            int(emission[1] * 255),
            int(emission[2] * 255),
            int(emission[3] * 255)

        )



        for loop_index in tri.loops:


            loop = mesh.loops[
                loop_index
            ]


            vert = mesh.vertices[
                loop.vertex_index
            ]



            #
            # Position
            #

            world_pos = (
                obj.matrix_world @ vert.co
            )


            x = world_pos.x
            y = world_pos.z
            z = -world_pos.y



            #
            # Normal
            #

            world_normal = (
                obj.matrix_world
                .to_3x3()
                @ vert.normal
            )


            world_normal.normalize()


            nx = world_normal.x
            ny = world_normal.z
            nz = -world_normal.y



            #
            # UV
            #

            if mesh.uv_layers:

                uv = (
                    mesh
                    .uv_layers
                    .active
                    .data[loop_index]
                    .uv
                )


                u = uv.x
                v = uv.y


            else:

                u = 0.0
                v = 0.0




            vertex = (

                x,
                y,
                z,

                nx,
                ny,
                nz,

                u,
                v,

                color[0],
                color[1],
                color[2],
                color[3]

            )



            if vertex not in vertex_lookup:

                vertex_lookup[vertex] = len(vertices)

                vertices.append(
                    vertex
                )



            indices.append(
                vertex_lookup[vertex]
            )



    return vertices, indices

TIMF_MAGIC = b"TIMF"
TIAF_MAGIC = b"TIAF"
FORMAT_VERSION = 1


def write_timf(filepath, vertices, indices):

    with open(filepath, "wb") as f:

        #
        # Header
        #

        f.write(TIMF_MAGIC)
        f.write(struct.pack("<I", FORMAT_VERSION))

        f.write(struct.pack("<I", len(vertices)))
        f.write(struct.pack("<I", len(indices)))

        #
        # Vertices
        #

        for vert in vertices:

            f.write(
                struct.pack(
                    "<8f4B",
                    *vert
                )
            )

        #
        # Indices
        #

        for index in indices:

            f.write(
                struct.pack(
                    "<H",
                    index
                )
            )


def write_tiaf(filepath, frames, indices):

    with open(filepath, "wb") as f:

        vertex_count = len(frames[0]) if frames else 0

        #
        # Header
        #

        f.write(TIAF_MAGIC)
        f.write(struct.pack("<I", FORMAT_VERSION))

        f.write(struct.pack("<I", len(frames)))
        f.write(struct.pack("<I", vertex_count))
        f.write(struct.pack("<I", len(indices)))

        #
        # Frame data
        #

        for frame in frames:

            for vert in frame:

                f.write(
                    struct.pack(
                        "<8f4B",
                        *vert
                    )
                )

        #
        # Shared indices
        #

        for index in indices:

            f.write(
                struct.pack(
                    "<H",
                    index
                )
            )


def export_mesh(objects, filepath):

    vertices = []
    indices = []

    for obj in objects:

        obj_vertices, obj_indices = collect_mesh_data(obj)

        offset = len(vertices)

        vertices.extend(obj_vertices)

        indices.extend(
            i + offset
            for i in obj_indices
        )

    write_timf(
        filepath,
        vertices,
        indices
    )

def export_animation(objects, filepath):

    scene = bpy.context.scene

    start = scene.frame_start
    end = scene.frame_end

    frames = []

    base_indices = None


    for frame in range(start, end + 1):

        print(
            "Exporting frame",
            frame
        )


        scene.frame_set(frame)


        frame_vertices = []
        frame_indices = []

        vertex_offset = 0



        for obj in objects:


            depsgraph = (
                bpy.context
                .evaluated_depsgraph_get()
            )


            evaluated = (
                obj
                .evaluated_get(depsgraph)
            )


            mesh = evaluated.to_mesh()



            vertices, indices = collect_mesh_data(
                obj,
                mesh
            )



            evaluated.to_mesh_clear()



            #
            # Add vertices
            #

            frame_vertices.extend(
                vertices
            )



            #
            # Fix indices because
            # multiple meshes are merged
            #

            frame_indices.extend(
                [
                    i + vertex_offset
                    for i in indices
                ]
            )



            vertex_offset += len(vertices)



        frames.append(
            frame_vertices
        )


        #
        # Topology should not change
        #

        if base_indices is None:

            base_indices = frame_indices



    name = clean_name(
        os.path.splitext(
            os.path.basename(filepath)
        )[0]
    )



    write_tiaf(
        filepath,
        frames,
        base_indices
    )