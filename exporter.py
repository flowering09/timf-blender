import bpy

from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty



class ExportWiiMesh(Operator, ExportHelper):

    bl_idname = "export_mesh.wii_h"
    bl_label = "Export Wii Engine Mesh"

    filename_ext = ".h"

    filter_glob: StringProperty(
        default="*.h",
        options={'HIDDEN'}
    )


    def execute(self, context):

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



        export_mesh(
            objects,
            self.filepath
        )


        self.report(
            {'INFO'},
            "Exported Wii mesh"
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





def export_mesh(objects, filepath):

    vertices = []
    indices = []

    vertex_lookup = {}



    #
    # Export every selected object
    #

    for obj in objects:

        mesh = obj.data

        mesh.calc_loop_triangles()



        #
        # Materials
        #

        materials = []


        for mat in mesh.materials:

            emission = get_emission_color(
                mat
            )


            materials.append(
                emission
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
                # Transform position
                #

                world_pos = obj.matrix_world @ vert.co

                x = world_pos.x
                y = world_pos.z
                z = -world_pos.y



                #
                # Transform normal
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

                    # position

                    x,
                    y,
                    z,


                    # normal

                    nx,
                    ny,
                    nz,


                    # UV

                    u,
                    v,


                    # color

                    color[0],
                    color[1],
                    color[2],
                    color[3]

                )



                if vertex not in vertex_lookup:

                    vertex_lookup[
                        vertex
                    ] = len(vertices)


                    vertices.append(
                        vertex
                    )



                indices.append(
                    vertex_lookup[vertex]
                )




    name = clean_name(
        objects[0].name
    )



    with open(filepath, "w") as f:


        f.write(
            "#pragma once\n\n"
        )


        f.write(
            '#include "vertex.h"\n\n'
        )



        #
        # Vertices
        #

        f.write(
            f"static Vertex {name}_vertices[] = {{\n"
        )


        for vert in vertices:

            f.write(
                "    { "
                +
                ", ".join(
                    f"{x:.6f}f"
                    for x in vert[:8]
                )
                +
                ", "
                +
                ", ".join(
                    str(x)
                    for x in vert[8:]
                )
                +
                " },\n"
            )


        f.write(
            "};\n\n"
        )



        #
        # Indices
        #

        f.write(
            f"static unsigned short {name}_indices[] = {{\n"
        )


        for i in range(
            0,
            len(indices),
            3
        ):

            f.write(
                f"    {indices[i]}, "
                f"{indices[i+1]}, "
                f"{indices[i+2]},\n"
            )


        f.write(
            "};\n\n"
        )



        #
        # Mesh
        #

        f.write(
            f"static Mesh {name}_mesh = {{\n"
        )


        f.write(
            f"    {name}_vertices,\n"
        )


        f.write(
            f"    {len(vertices)},\n"
        )


        f.write(
            f"    {name}_indices,\n"
        )


        f.write(
            f"    {len(indices)}\n"
        )


        f.write(
            "};\n"
        )