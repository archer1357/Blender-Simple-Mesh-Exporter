##Blender Simple Mesh Exporter

Exports scene meshes and materials to JSON.

Blender 2.6+.

#####Exports:
* vertices and indices as an array or a base 64 string
* vertex positions
  * xyz
* vertex normals
  * smoothed on 'smooth faces'
  * weighted by triangle area and angle at vertex
  * optional
  * xyz
* vertex texcoords
  * for each uv layer
  * optional
  * st
* vertex tangents
  * for each uv layer
  * smoothed separately for smooth/flat faces
  * weighted by triangle area and angle at vertex
  * optional
  * xyzw
* vertex colours
  * for each colour layer
  * optional
  * rgb
* vertex material colours
  * optional
  * rgb
* indices
  * integer or short data type
  * grouped by material
  * as adjacency list
    * missing adjacency index is equal to the vertices count
    * breaks adjacency on triangles with area less than epsilon
    * breaks adjacency on edges with more than two triangles
    * optional
* material names
  * indices offset/size
  * colour, roughness, intensity, etc
  

#####Missing:
* doesn't find the best break for quads

#####Example:
```json
{
  "vertices_count" : 4,
  "indices_count" : 6,
  "positions" : "AACAvwAAAAAAAIA/AACAPwAAAAAAAIA/AACAPwAAAAAAAIC/AACAvwAAAAAAAIC/",
  "normals" : "AAAAAP//fz8AAAAAAAAAAAAAgD8AAAAAAAAAAP//fz8AAAAAAAAAAAAAgD8AAAAA",
  "texcoords" : {
    "UV1" : "W6zROFus0Thw+X8/mtnROHD5fz9y+X8/W6zROHD5fz8=",
    "UV2" : "auQQP7YYmj+4xVC+bOQQPyQ33j64xVC+tRiaPyg33j4="
  },
  "tangents" : {
    "UV1" : "AACAPwAAAAAzidozAACAPwAAgD8AAAAARwW1MwAAgD8AAIA/AAAAADOJ2jMAAIA/AACAPwAAAACPBgA0AACAPw==",
    "UV2" : "8R9FvwAAAABeVSO/AACAP/IfRb8AAAAAXVUjvwAAgD/xH0W/AAAAAF5VI78AAIA/8B9FvwAAAABgVSO/AACAPw=="
  },
  "colors" : {
    "Col1" : "AACAPwAAgD8AAIA/AACAPwAAgD8AAIA/AACAPwAAgD8AAIA/AACAPwAAgD8AAIA/",
    "Col2" : "AACAP+/ubj/f3t4+AACAP7CvLz+pqCg/7exsPgAAgD/l5OQ+nZwcPoGAgDsAAIA/"
  },
  "indices" : "AAABAAIAAwAAAAIA",
  "materials" : {
    "Material" : {
      "draw_first" : 0,
      "draw_count" : 3,
      "color" : [0.0404854,0.8,0.254439,1],
      "emit" : 0,
      "fresnel" : 0.1,
      "fresnel_factor" : 0.5,
      "roughness" : 0.5,
      "hardness" : 50,
      "intensity" : 0.5
    },
    "Material.001" : {
      "draw_first" : 3,
      "draw_count" : 3,
      "color" : [0.8,0.0773564,0.533169,1],
      "emit" : 0,
      "fresnel" : 0.1,
      "fresnel_factor" : 0.5,
      "roughness" : 0.5,
      "hardness" : 50,
      "intensity" : 0.5
    }
  }
}
```
