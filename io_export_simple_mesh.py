
bl_info = {
  "name": "Simple Mesh Exporter",
  "author": "me",
  "version": (1,0,0),
  "blender": (2,6,2),
  "location": "File > Export",
  "description": "Export my custom data format",
  "warning": "",
  "wiki_url": "",
  "tracker_url": "",
  "category" : "Import-Export"}

import bpy,bmesh,bpy_extras,struct,os,mathutils,functools,base64,math,re

def orthog_vec(nor,vec):
  r=(vec - nor * nor.dot(vec))
  r.normalize()
  return r

def calc_tangent_space(pt1,pt2,pt3,uv1,uv2,uv3,nor):
  e1=pt2-pt1
  e2=pt3-pt1
  e1uv=uv2-uv1
  e2uv=uv3-uv1

  cp=e1uv.x*e2uv.y - e1uv.y*e2uv.x

  if cp == 0.0:
    return mathutils.Vector((0,0,0,0))

  r = 1.0 / cp
  sdir=(e2uv.y*e1 - e1uv.y*e2)*r
  tdir=(e1uv.x*e2 - e2uv.x*e1)*r
  tg=(sdir - nor * nor.dot(sdir)).normalized()
  w=-1.0 if nor.cross(sdir).dot(tdir) < 0.0 else 1.0

  return mathutils.Vector((tg.x,tg.y,tg.z,w))

def calc_vec_angle(v0,v1):
  l=v0.length*v1.length
  d=v0.dot(v1)
  a=math.acos(d/l)
  return a

def calc_triangle_area(p0,p1,p2):
  e0=p1-p0
  e1=p2-p0
  c=e0.cross(e1)
  # l=math.sqrt(c.dot(c))
  a=c.length/2.0
  return a

def do_mesh(me,modelMat,normalMat,useNormals,useTexcoords,
            useTangents,useColors,useFlat,useMaterialColors,
            useSelectedFaces):

  me.update(calc_tessface=True)

  my_verts_num=0
  my_inds_num=0

  my_positions=[]
  my_normals=[]
  my_colors=dict([(x.name,[]) for x in me.vertex_colors])
  my_texcoords=dict([(x.name,[]) for x in me.uv_textures])
  my_tangents=dict([(x.name,[]) for x in me.uv_textures])
  my_matCols=[]

  my_vert_inds=dict()
  my_indices=dict([(ma.name if ma != None else "",[]) for ma in me.materials] if me.materials else [("",[])])
  orig_vert_inds=[]

  #
  faceTriVertInds=[] #[faceInd][triInd]=[0,1,2]/[0,2,3]
  faceTriNors=[] #[faceInd][triInd]=nor
  uvFaceTriTangs=[] #[uvInd][faceInd]=[tri0Tang,tri1Tang]
  vertFaceTris=[[] for x in me.vertices] #[vertInd]=[[faceInd,triInd,triVertInd],...]
  
  #face triangulation inds
  for faceInd, face in enumerate(me.tessfaces):
    if len(face.vertices)==4:
      #todo: find best split
      faceTriVertInds.append([[0,1,2],[0,2,3]])
    else:
      faceTriVertInds.append([[0,1,2]])

  #
  for faceInd, face in enumerate(me.tessfaces):
    for triInd,triVertInds in enumerate(faceTriVertInds[faceInd]):
      for i,triVertInd in enumerate(triVertInds):
        vertInd=face.vertices[triVertInd]
        vertFaceTris[vertInd].append([faceInd,triInd,i])
      
  #face triangulated nors
  for faceInd, face in enumerate(me.tessfaces):
    nors=[]

    for triVertInds in faceTriVertInds[faceInd]:
      pt1=me.vertices[face.vertices[triVertInds[0]]].co
      pt2=me.vertices[face.vertices[triVertInds[1]]].co
      pt3=me.vertices[face.vertices[triVertInds[2]]].co

      e1=pt2-pt1
      e2=pt3-pt1

      nor=e1.cross(e2)
      nor.normalize()
      nors.append(nor)

    faceTriNors.append(nors)

  #
  
  if useTangents:
    for uvInd,uvtex in enumerate(me.uv_textures):
      uvFaceTriTangs.append([])

      for faceInd, face in enumerate(me.tessfaces):
        tcs=[]
        pts=[]

        #
        uvFaceTriTangs[uvInd].append([])

        #face texcoords
        tcs.append(me.tessface_uv_textures[uvInd].data[faceInd].uv1)
        tcs.append(me.tessface_uv_textures[uvInd].data[faceInd].uv2)
        tcs.append(me.tessface_uv_textures[uvInd].data[faceInd].uv3)

        if len(face.vertices)==4:
          tcs.append(me.tessface_uv_textures[uvInd].data[faceInd].uv4)

        #face verts
        for vertInd in face.vertices:
          pts.append(me.vertices[vertInd].co)

        for triInd,triVertInds in enumerate(faceTriVertInds[faceInd]):
          nor=faceTriNors[faceInd][triInd]

          tang=calc_tangent_space(pts[triVertInds[0]],pts[triVertInds[1]],pts[triVertInds[2]],
                                  tcs[triVertInds[0]],tcs[triVertInds[1]],tcs[triVertInds[2]],
                                  nor)

          uvFaceTriTangs[uvInd][faceInd].append(tang)

  #gen vert+index for each poly
  for faceInd, face in enumerate(me.tessfaces):
    if useSelectedFaces and not face.select:
      continue

    #
    ma=me.materials[face.material_index] if me.materials else None
    maName=(ma.name if ma != None else "") if me.materials else ""
    face_cols = [[] for x in me.vertex_colors]

    #
    if useColors:
      for i,x in enumerate(me.vertex_colors):
        face_cols[i].append(me.tessface_vertex_colors[i].data[faceInd].color1)
        face_cols[i].append(me.tessface_vertex_colors[i].data[faceInd].color2)
        face_cols[i].append(me.tessface_vertex_colors[i].data[faceInd].color3)

        if len(face.vertices)==4:
          face_cols[i].append(me.tessface_vertex_colors[i].data[faceInd].color4)

    if useTexcoords or useTangents:
      face_uvs = [[] for x in me.uv_textures]

      for i,x in enumerate(me.uv_textures):
        face_uvs[i].append(me.tessface_uv_textures[i].data[faceInd].uv1)
        face_uvs[i].append(me.tessface_uv_textures[i].data[faceInd].uv2)
        face_uvs[i].append(me.tessface_uv_textures[i].data[faceInd].uv3)

        if len(face.vertices)==4:
          face_uvs[i].append(me.tessface_uv_textures[i].data[faceInd].uv4)

    #
    for triInd,triVertInds in enumerate(faceTriVertInds[faceInd]):
      for triVertInd in triVertInds:
        key=''
        cols=[]
        uvs=[]
        tangs=[]
        vertInd=face.vertices[triVertInd]

        pos=me.vertices[vertInd].co
        nor=None

        if useNormals or useTangents:
          if face.use_smooth:
            nor=mathutils.Vector((0,0,0))

            for x in vertFaceTris[vertInd]:
              faceInd2=x[0]
              triInd2=x[1]
              face2=me.tessfaces[faceInd2]
              triVertInds2=faceTriVertInds[faceInd2][triInd2]
              
              p0=me.vertices[face2.vertices[triVertInds2[x[2]%3]]].co
              p1=me.vertices[face2.vertices[triVertInds2[(x[2]+1)%3]]].co
              p2=me.vertices[face2.vertices[triVertInds2[(x[2]+2)%3]]].co
                
              if face2.use_smooth:
                nor2=faceTriNors[faceInd2][triInd2]
                area=calc_triangle_area(p0,p1,p2)
                angle=calc_vec_angle(p2-p0,p1-p0)
                #nor=nor+nor2.xyz*angle*area
                nor=nor+nor2.xyz*(angle+area)
                #nor=nor+nor2.xyz*area
                #nor=nor+nor2.xyz*angle

            nor.normalize()
              
          else:
            nor=faceTriNors[faceInd][triInd]

        #
        key+=' %g %g %g'%(pos[0],pos[1],pos[2])

        if useNormals:
          key+=' %g %g %g'%(nor[0],nor[1],nor[2])

        #
        if useColors:
          for face_col in face_cols:
            col=face_col[triVertInd]
            cols.append(col)
            key+=' %g %g %g'%(col[0],col[1],col[2])

        if useTexcoords:
          for face_uv in face_uvs:
            uv=face_uv[triVertInd]
            uvs.append(uv)
            key+=' %g %g'%(uv[0],uv[1])

        #
        matCol=None

        if useMaterialColors:
          matCol=ma.diffuse_color if ma else [1.0,1.0,1.0]
          key+=' %g %g %g'%(matCol[0],matCol[1],matCol[2])

        #
        if useTangents:
          for uvInd,uvtex in enumerate(me.uv_textures):
            #todo: check mirroring via dot( cross( T, B ), N ) ?
            tang=None
            triTang=uvFaceTriTangs[uvInd][faceInd][triInd]
            
            if triTang.w==0:
              tang=triTang
            elif face.use_smooth:
              avgTang=mathutils.Vector((0,0,0))
              
              for x in vertFaceTris[vertInd]:
                faceInd2=x[0]
                triInd2=x[1]
                face2=me.tessfaces[faceInd2]
                tang2=uvFaceTriTangs[uvInd][faceInd2][triInd2]
                triVertInds2=faceTriVertInds[faceInd2][triInd2]
                
                p0=me.vertices[face2.vertices[triVertInds2[x[2]%3]]].co
                p1=me.vertices[face2.vertices[triVertInds2[(x[2]+1)%3]]].co
                p2=me.vertices[face2.vertices[triVertInds2[(x[2]+2)%3]]].co
                
                if face2.use_smooth:
                  if tang2.w==triTang.w and tang2.xyz.dot(triTang.xyz)>0:
                    area=calc_triangle_area(p0,p1,p2)
                    angle=calc_vec_angle(p2-p0,p1-p0)
                    #avgTang=avgTang+tang2.xyz*angle*area
                    avgTang=avgTang+tang2.xyz*(angle+area)
            
              avgTang.normalize()
              avgTang=orthog_vec(nor,avgTang)
              tang=mathutils.Vector((avgTang.x,avgTang.y,avgTang.z,triTang.w))
              
            else:
              if False:
                #no smoothing
                tang=triTang
              else:
                avgTang=mathutils.Vector((0,0,0))
              
                for x in vertFaceTris[vertInd]:
                  faceInd2=x[0]
                  triInd2=x[1]
                  face2=me.tessfaces[faceInd2]
                  nor2=faceTriNors[faceInd2][triInd2]
                  tang2=uvFaceTriTangs[uvInd][faceInd2][triInd2]
                  triVertInds2=faceTriVertInds[faceInd2][triInd2]
                  
                  p0=me.vertices[face2.vertices[triVertInds2[x[2]%3]]].co
                  p1=me.vertices[face2.vertices[triVertInds2[(x[2]+1)%3]]].co
                  p2=me.vertices[face2.vertices[triVertInds2[(x[2]+2)%3]]].co
                
                  if not face2.use_smooth:
                    if nor.x==nor2.x and nor.y==nor2.y and nor.z==nor2.z:
                      if tang2.w==triTang.w and tang2.xyz.dot(triTang.xyz)>0:
                        area=calc_triangle_area(p0,p1,p2)
                        angle=calc_vec_angle(p2-p0,p1-p0)
                        #avgTang=avgTang+tang2.xyz*angle*area
                        avgTang=avgTang+tang2.xyz*(angle+area)
            
                avgTang.normalize()
                avgTang=orthog_vec(nor,avgTang)
                tang=mathutils.Vector((avgTang.x,avgTang.y,avgTang.z,triTang.w))
  
            tangs.append(tang)
            key+=' %g %g %g %g'%(tang[0],tang[1],tang[2],tang[3])

        #
        if key not in my_vert_inds.keys():
          orig_vert_inds.append(vertInd)

          my_vert_inds[key]=my_verts_num
          my_positions.append(pos)

          if useNormals:
            my_normals.append(nor)

          if useColors:
            for i,vertcol in enumerate(me.vertex_colors):
              my_colors[vertcol.name].append(cols[i])
          if useTexcoords:
            for i,uvtex in enumerate(me.uv_textures):
              my_texcoords[uvtex.name].append(uvs[i])

          if useTangents:
            for i,uvtex in enumerate(me.uv_textures):
              my_tangents[uvtex.name].append(tangs[i])

          if useMaterialColors:
            my_matCols.append(matCol)

          my_verts_num+=1

        my_vert_indice=my_vert_inds[key]
        my_indices[maName].append(my_vert_indice)
        my_inds_num+=1

    #
    # if face.area < 1.0e-4:
    #   # print("a:",[i for i in face.vertices])


    #   print("a:",ccccc,face.area)

    # xxx= [modelMat*me.vertices[vertInd].co for faceVertInd,vertInd in enumerate(face.vertices)]
    # arr=calc_triangle_area(xxx[0],xxx[1],xxx[2])
    # if arr < 1.0e-5:
    #   print("b:",ccccc,arr)

    # ccccc=ccccc+1

  #apply transforms
  for i,x in enumerate(my_positions):
    my_positions[i]=modelMat*x;

  for i,x in enumerate(my_normals):
    my_normals[i]=normalMat*x;

  for k,v in my_tangents.items():
    for i,tg in enumerate(v):
      w=tg.w
      tg2=normalMat*tg.xyz
      my_tangents[k][i]=mathutils.Vector((tg2[0],tg2[1],tg2[2],w));

  #
  return {
    "positions" : my_positions,
    "normals" : my_normals,
    "texcoords" : my_texcoords,
    "tangents" : my_tangents,
    "colors" :  my_colors,
    "material_colors" : my_matCols,
    "indices" : my_indices,
    "vertices_num" : my_verts_num,
    "indices_num" : my_inds_num
  }

def calc_halfedges(halfEdges,verts,inds):
  for i in range(0,int(len(inds)//3)):
    ind0=inds[i*3+0]
    ind1=inds[i*3+1]
    ind2=inds[i*3+2]

    vs0=verts[ind0*3:ind0*3+3] #vert length is 4 for adjacency (has been changed to 3)
    vs1=verts[ind1*3:ind1*3+3]
    vs2=verts[ind2*3:ind2*3+3]

    # print(len(vs0),len(vs1),len(vs2),
    #       ",", len(out["vertices"]["positions"]["data"]),
    #       ",", ind0*3,ind1*3,ind2*3)

    v0=mathutils.Vector(vs0)
    v1=mathutils.Vector(vs1)
    v2=mathutils.Vector(vs2)

    area=calc_triangle_area(v0,v1,v2)

    # if area < 1.0e-5:
    #   print("b:",[ind0,ind1,ind2])

    key0="%i %i"%(ind0,ind1)
    key1="%i %i"%(ind1,ind2)
    key2="%i %i"%(ind2,ind0)

    if key0 not in halfEdges.keys():
      halfEdges[key0]=[]

    if key1 not in halfEdges.keys():
      halfEdges[key1]=[]

    if key2 not in halfEdges.keys():
      halfEdges[key2]=[]

    halfEdges[key0].append((ind2,area))
    halfEdges[key1].append((ind0,area))
    halfEdges[key2].append((ind1,area))

  return halfEdges

def calc_adjacency(halfEdges,inds):
  inds2=[]

  for i in range(0,int(len(inds)//3)):
    ind0=inds[i*3+0]
    ind1=inds[i*3+1]
    ind2=inds[i*3+2]

    key0="%i %i"%(ind1,ind0)
    key1="%i %i"%(ind2,ind1)
    key2="%i %i"%(ind0,ind2)

    f0=halfEdges.get(key0,[])
    f1=halfEdges.get(key1,[])
    f2=halfEdges.get(key2,[])

    # print(f0,f1,f2)

    ff0=f0[0] if len(f0)==1 else None
    ff1=f1[0] if len(f1)==1 else None
    ff2=f2[0] if len(f2)==1 else None

    fffInd0 = ff0[0] if ff0 != None else -1
    fffInd1 = ff1[0] if ff1 != None else -1
    fffInd2 = ff2[0] if ff2 != None else -1

    fffArea0 = ff0[1] if ff0 != None else 0
    fffArea1 = ff1[1] if ff1 != None else 0
    fffArea2 = ff2[1] if ff2 != None else 0

    rkey0="%i %i"%(ind0,ind1)
    rkey1="%i %i"%(ind1,ind2)
    rkey2="%i %i"%(ind2,ind0)

    g0=halfEdges.get(rkey0,[])
    g1=halfEdges.get(rkey1,[])
    g2=halfEdges.get(rkey2,[])

    gg0=g0[0] if len(g0)==1 else None
    gg1=g1[0] if len(g1)==1 else None
    gg2=g2[0] if len(g2)==1 else None

    gggArea0 = gg0[1] if gg0 != None else 0
    gggArea1 = gg1[1] if gg1 != None else 0
    gggArea2 = gg2[1] if gg2 != None else 0

    rlen0=len(g0)
    rlen1=len(g1)
    rlen2=len(g2)

    epsilon=1.0e-5

    aaa=[inds[i*3], #0
         # fffInd0 if rlen0==1 else -1, #1
         -1 if fffArea0<epsilon or gggArea0<epsilon or rlen0!=1 else fffInd0,
         inds[i*3+1], #2
         # fffInd1 if rlen1==1 else -1,#3
         -1 if fffArea1<epsilon or gggArea1<epsilon or rlen1!=1 else fffInd1,
         inds[i*3+2], #4
         # fffInd2 if rlen2==1 else -1 #5
         -1 if fffArea2<epsilon or gggArea2<epsilon or rlen2!=1 else fffInd2
    ]

    inds2.extend(aaa)

  #
  #holes_count=0

  #for i in inds2:
  #  if i==-1:
  #    holes_count+=1

  #print("adjacency: holes %i, nonholes %i"%(holes_count,len(inds2)-holes_count))

  #
  return inds2

def remove_dupls(values):
  output = []
  seen = set()

  for value in values:
    if value not in seen:
      output.append(value)
      seen.add(value)

  return output

def do_meshes(useSelected,useNormals,
              useTexcoords,useTangents,
              useColors,
              useTransform,useUShortIndices,
              useAdjacent,useAdjacentNoneW,
              useFlat,
              useMaterialColors, useYUp,
              useSelectedFaces,useLeftHanded):
  all=not (useSelected and bpy.context.selected_objects)
  objects=bpy.data.objects if all else bpy.context.selected_objects
  objects2=[ob for ob in objects if ob.type == "MESH"]

  #rotY(-pi/2)*rotX(-pi/2)=[0,0,-1, 0,1,0, 1,0,0]*[1,0,0, 0,0,1, 0,-1,0]=[0,1,0, 0,0,1, 1,0,0]

  fixModelMat=mathutils.Matrix([[0,1,0,0],[0,0,1,0],[1,0,0,0],[0,0,0,1]]) if useYUp else mathutils.Matrix.Identity(4)
  fixNormalMat=mathutils.Matrix([[0,1,0],[0,0,1],[1,0,0]]) if useYUp else mathutils.Matrix.Identity(3)

  #if useLeftHanded:
  #  fixModelMat=fixModelMat*mathutils.Matrix([[-1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]])
  #  fixNormalMat=fixNormalMat*mathutils.Matrix([[-1,0,0],[0,1,0],[0,0,1]])

  #fixModelMat=(mathutils.Matrix.Rotation(-math.pi/2.0,4,'Y')*
  #             mathutils.Matrix.Rotation(-math.pi/2.0,4,'X')
  #             if useYUp else mathutils.Matrix.Identity(4))

  #fixNormalMat=fixModelMat.to_3x3()


  out={
    "positions" : [],
    "indices" : [],
    "material_names" : [],
    "materials" : {}
  }

  uvLayers=[]
  colLayers=[]
  vertsOffset=0


  #
  if useTexcoords or useTangents:
    for ob in objects2:
      for x in ob.data.uv_textures:
        uvLayers.append(x.name)

  if useColors:
    for ob in objects2:
      for x in ob.data.vertex_colors:
        colLayers.append(x.name)


  #
  uvLayers=remove_dupls(uvLayers)
  colLayers=remove_dupls(colLayers)

  #init containers to hold combined vertices/indices from objects
  if useNormals:
    out["normals"]=[]

  if useTexcoords and len(uvLayers)>0:
    out["texcoords"]={}

    for uv in uvLayers:
      out["texcoords"][uv]=[]

  if useTangents and len(uvLayers)>0:
    out["tangents"]={}

    for uv in uvLayers:
      out["tangents"][uv]=[]

  if useColors and len(colLayers)>0:
    out["colors"]={}

  if useMaterialColors:
    out["material_colors"]=[]

  if useColors:
    for col in colLayers:
      out["colors"][col]=[]

  indices_out=dict() #[mat][obj]

  #get object meshes
  for ob in objects2:
    #print(ob.name)

    worldMat=fixModelMat*ob.matrix_world if useTransform else fixModelMat
    # normalMat=fixNormalMat*ob.matrix_world.normalized().to_3x3() if useTransform else fixNormalMat

    normalMat=fixNormalMat

    if useTransform:
      normalMat=worldMat.copy()
      normalMat.invert()
      normalMat.transpose()
      normalMat=normalMat.to_3x3()



    #
    myme=do_mesh(ob.data,worldMat,normalMat,useNormals,useTexcoords,
                 useTangents,
                 useColors,useFlat,useMaterialColors,
                 useSelectedFaces)

    #combine vertices/indices and fill in blank vertices
    #positions
    if useAdjacent and useAdjacentNoneW:
      out["positions"].extend([0.0,0.0,0.0,0.0])

    for pos in myme["positions"]:
      out["positions"].extend(pos)
      
      if useAdjacent and useAdjacentNoneW:
        out["positions"].append(1)

    #normals
    if useNormals:
      if useAdjacent and useAdjacentNoneW:
        out["normals"].extend([0.0,0.0,0.0])
      
      for nor in myme["normals"]:
        out["normals"].extend(nor)

    #texcoords
    if useTexcoords:
      #hasnt
      for uv in uvLayers:
        if uv not in myme["texcoords"].keys():
          if useAdjacent and useAdjacentNoneW:
            out["texcoords"][uv].extend([0.0,0.0])
            
          for i in range(0,myme["vertices_num"]*2):
            out["texcoords"][uv].append(0.0)

      #has
      for uv,texs in myme["texcoords"].items():
        if useAdjacent and useAdjacentNoneW:
          out["texcoords"][uv].extend([0.0,0.0])
          
        for tex in texs:
          out["texcoords"][uv].extend(tex)

    #tangents
    if useTangents:
      #hasnt
      for uv in uvLayers:
        if uv not in myme["tangents"].keys():
          if useAdjacent and useAdjacentNoneW:
            out["tangents"][uv].extend([0.0,0.0,0.0,0.0])
            
          for i in range(0,myme["vertices_num"]*4):
            out["tangents"][uv].append(0.0)

      #has
      for uv,tgs in myme["tangents"].items():
        if useAdjacent and useAdjacentNoneW:
          out["tangents"][uv].extend([0.0,0.0,0.0,0.0])
          
        for tg in tgs:
          out["tangents"][uv].extend(tg)

    #material colors
    if useMaterialColors:
      if useAdjacent and useAdjacentNoneW:
        out["material_colors"].extend([0.0,0.0,0.0])
        
      for matCol in myme["material_colors"]:
        out["material_colors"].extend(matCol)

    #colors
    if useColors:
      #hasnt
      for c in colLayers:
        if c not in myme["colors"].keys():
          if useAdjacent and useAdjacentNoneW:
            out["colors"][c].extend([0.0,0.0,0.0])
            
          for i in range(0,myme["vertices_num"]*3):
            out["colors"][c].append(1.0)

      #has
      for c,cols in myme["colors"].items():
        if useAdjacent and useAdjacentNoneW:
          out["colors"][c].extend([0.0,0.0,0.0])
          
        for col in cols:
          out["colors"][c].extend(col)

    #indices
    for ma,inds in myme["indices"].items():
      if ma not in indices_out.keys():
        indices_out[ma]=dict()

      if ob.name not in indices_out[ma].keys():
        indices_out[ma][ob.name]=[]

      indices_out[ma][ob.name].extend([x+vertsOffset for x in inds])

    #
    # vertsOffset+=len(myme["positions"])
    vertsOffset+=myme["vertices_num"]

  #
  halfEdges={}

  #
  if useAdjacent:
    for ma,obInds in indices_out.items():
      for ob,inds in obInds.items():
        calc_halfedges(halfEdges,out["positions"],inds)

  #todo also check empty string material name not in bpy.data.materials
  if "" in indices_out.keys():
    mtrl={}
    mtrl["name"]=""
    mtrl["alpha"]=1.0
    mtrl["color"]=[0.8,0.8,0.8]
    mtrl["fresnel"]=0.1
    mtrl["fresnel_factor"]=0.5
    mtrl["emit"]=0.0
    mtrl["roughness"]=0.5
    mtrl["hardness"]=50.0
    mtrl["intensity"]=0.5
    out["materials"][""]=mtrl
    out["material_names"].append("")

  #
  for ma in bpy.data.materials:
    if ma!=None and ma.name in indices_out.keys():
      mtrl={}
      mtrl["alpha"]=ma.alpha
      mtrl["color"]=ma.diffuse_color
      mtrl["fresnel"]=ma.diffuse_fresnel
      mtrl["fresnel_factor"]=ma.diffuse_fresnel_factor
      mtrl["emit"]=ma.emit
      mtrl["roughness"]=ma.roughness
      mtrl["hardness"]=ma.specular_hardness
      mtrl["intensity"]=ma.specular_intensity
      out["materials"][ma.name]=mtrl
      out["material_names"].append(ma.name)

  #
  for ma in out["material_names"]:
    obInds=indices_out[ma]

    outInds=out["indices"]
    first=len(outInds)
    first2=first
    count=0

    for ob,inds in obInds.items():
      count2=len(inds)

      #
      if useAdjacent:
        inds2=calc_adjacency(halfEdges,inds)

        #set nonadj index
        for i,x in enumerate(inds2):
          if x==-1:
            if useAdjacentNoneW:
              inds2[i]=0
            else:
              inds2[i]=vertsOffset

        #
        outInds.extend(inds2)
      else:
        outInds.extend(inds)

      #
      count+=count2
      first2+=count2


      out["materials"][ma]["first"]=first
      out["materials"][ma]["count"]=count

  #
  inds_num=len(out["indices"])

  #
  out["uv_names"]=uvLayers
  out["color_names"]=colLayers
  out["indices_num"]=inds_num
  out["vertices_num"]=vertsOffset+(1 if useAdjacentNoneW else 0)
  
  

  return out

def meshes_toBytes(mes,useUShortIndices):
  inds_num=len(mes["indices"])

  type=""

  if useUShortIndices:
    type="H"
  else:
    type="I"

  b=struct.pack("%i%s"%(inds_num,type),*mes["indices"])
  mes["indices"]=b

  # for k,v in mes["vertices"].items():
  #   b=struct.pack("%if"%(len(v["data"])),*v)
  #   v=b


  b=struct.pack("%if"%(len(mes["positions"])),*mes["positions"])
  mes["positions"]=b

  if "normals" in mes.keys():
    b=struct.pack("%if"%(len(mes["normals"])),*mes["normals"])
    mes["normals"]=b

  if "texcoords" in mes.keys():
    for k,v in mes["texcoords"].items():
      b=struct.pack("%if"%(len(v)),*v)
      mes["texcoords"][k]=b

  if "tangents" in mes.keys():
    for k,v in mes["tangents"].items():
      b=struct.pack("%if"%(len(v)),*v)
      mes["tangents"][k]=b

  if "colors" in mes.keys():
    for k,v in mes["colors"].items():
      b=struct.pack("%if"%(len(v)),*v)
      mes["colors"][k]=b

  if "material_colors" in mes.keys():
    b=struct.pack("%if"%(len(mes["material_colors"])),
                  *mes["material_colors"])
    mes["material_colors"]=b

def meshes_toBase64(mes,useUShortIndices):
  meshes_toBytes(mes,useUShortIndices)

  b=base64.b64encode(mes["indices"]).decode("ascii")
  mes["indices"]=b

  b=base64.b64encode(mes["positions"]).decode("ascii")
  mes["positions"]=b

  if "normals" in mes.keys():
    b=base64.b64encode(mes["normals"]).decode("ascii")
    mes["normals"]=b

  if "texcoords" in mes.keys():
    for k,v in mes["texcoords"].items():
      b=base64.b64encode(v).decode("ascii")
      mes["texcoords"][k]=b

  if "tangents" in mes.keys():
    for k,v in mes["tangents"].items():
      b=base64.b64encode(v).decode("ascii")
      mes["tangents"][k]=b

  if "colors" in mes.keys():
    for k,v in mes["colors"].items():
      b=base64.b64encode(v).decode("ascii")
      mes["colors"][k]=b

  if "material_colors" in mes.keys():
    b=base64.b64encode(mes["material_colors"]).decode("ascii")
    mes["material_colors"]=b


def writeJsonNumArray(fh,name,vals,useBase64,indent,isVerts,isEnd):
  space=' '*indent
  header='%s"%s" : '%(space,name)

  fh.write(header)

  if useBase64:
    fh.write('"')
    fh.write(vals)
    fh.write('"')
  else:
    fh.write('[')
    posLen=len(vals)
    headerLen=len(header)
    sTotalLen=headerLen

    for i,x in enumerate(vals):
      if sTotalLen>80:
        fh.write('\n')
        sTotalLen=headerLen
        fh.write(' '*(headerLen+1))

      if isVerts:
        # s='%0.7f'%(x)
        s='%g'%(x)
        # s='%.3g'%(x)
        # s='{:.2e}'.format(x)

      else:
        s='%i'%(x)

      if i!=posLen-1:
        s+=','

      sTotalLen+=len(s)


      fh.write(s)

    fh.write(']')

  if not isEnd:
    fh.write(',')

  fh.write('\n')


class MyExportJson(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
  bl_idname = "my_export.json";
  bl_label = "Export";
  bl_options = {'PRESET'};
  filename_ext = ".json";

  useNormals=bpy.props.BoolProperty(name="normals",default=True)
  useTexcoords=bpy.props.BoolProperty(name="texcoords",default=False)
  useTangents=bpy.props.BoolProperty(name="tangents",default=False)
  useColors=bpy.props.BoolProperty(name="colors",default=False)
  useMaterialColors=bpy.props.BoolProperty(name="material colors",default=False)
  # useYUp=bpy.props.BoolProperty(name="y-axis up",default=True)
  # useLeftHanded=bpy.props.BoolProperty(name="left-handed",default=False)
  # useFlat=bpy.props.BoolProperty(name="flat shading",default=False)
  useAdjacent=bpy.props.BoolProperty(name="adjacency",default=False)
  #useAdjacentNoneW=bpy.props.BoolProperty(name="adjacency broken w0",default=False)
  useUShortIndices=bpy.props.BoolProperty(name="short indices",default=False)
  # indent=bpy.props.IntProperty(name="json indent",default=2,min=0,max=8,step=1)
  indent=2
  useBase64=bpy.props.BoolProperty(name="base64",default=True)
  useTransform=bpy.props.BoolProperty(name="transform",default=True)
  useSelected=bpy.props.BoolProperty(name="selected",default=False)
  # useSelectedFaces=bpy.props.BoolProperty(name="selected faces",default=False)

  def execute(self, context):
    with open(self.filepath, 'w', encoding='utf-8') as fh:
      indentAmount=indent=None if self.indent==0 else self.indent
      mes=do_meshes(self.useSelected,self.useNormals,
                    self.useTexcoords,self.useTangents,
                    self.useColors,
                    self.useTransform,self.useUShortIndices,
                    self.useAdjacent,False,
                    False, #self.useFlat,
                    self.useMaterialColors,
                    True, #self.useYUp,
                    False, #self.useSelectedFaces,
                    False # self.useLeftHanded

                    )



      if self.useBase64:
        meshes_toBase64(mes,self.useUShortIndices)

      #
      fh.write('{\n')

      vertsNum=mes["vertices_num"]
      indsNum=mes["indices_num"]

      #
      fh.write('%s"vertices_count" : %i,\n'%(' '*self.indent,vertsNum))
      fh.write('%s"indices_count" : %i,\n'%(' '*self.indent,indsNum))

      #print(vertsNum);
      #print(indsNum);

      #positions
      writeJsonNumArray(fh,"positions",mes["positions"],
                        self.useBase64,self.indent,True,False)

      #normals
      if "normals" in mes.keys():
        writeJsonNumArray(fh,"normals",mes["normals"],
                          self.useBase64,self.indent,True,False)

      #
      uvNamesLen=len(mes["uv_names"])

      #texcoords
      if "texcoords" in mes.keys():
        fh.write('%s"texcoords" : {\n'%(' '*self.indent))

        for i,v in enumerate(mes["uv_names"]):
          writeJsonNumArray(fh,v,mes["texcoords"][v],
                            self.useBase64,self.indent*2,True,i==uvNamesLen-1)

        fh.write('%s},\n'%(' '*self.indent))


      #tangents
      if "tangents" in mes.keys():
        fh.write('%s"tangents" : {\n'%(' '*self.indent))

        for i,v in enumerate(mes["uv_names"]):
          writeJsonNumArray(fh,v,mes["tangents"][v],
                            self.useBase64,self.indent*2,True,i==uvNamesLen-1)

        fh.write('%s},\n'%(' '*self.indent))


      #
      colNamesLen=len(mes["color_names"])

      #colors
      if "colors" in mes.keys():
        fh.write('%s"colors" : {\n'%(' '*self.indent))

        for i,v in enumerate(mes["color_names"]):
          writeJsonNumArray(fh,v,mes["colors"][v],
                            self.useBase64,self.indent*2,True,i==colNamesLen-1)

        fh.write('%s},\n'%(' '*self.indent))

      #material_colors
      if "material_colors" in mes.keys():
        writeJsonNumArray(fh,"material_colors",mes["material_colors"],
                          self.useBase64,self.indent,True,False)

      #indices
      writeJsonNumArray(fh,"indices",mes["indices"],
                        self.useBase64,self.indent,False,False)

      #materials
      fh.write('%s"materials" : {\n'%(' '*self.indent))

      for i,n in enumerate(mes["material_names"]):
        v=mes["materials"][n]

        s='%s"%s" : {\n'%(' '*(self.indent*2),n)
        # s+='%s"alpha" : %g,\n'%(' '*(self.indent*3),v["alpha"])
        s+='%s"draw_first" : %i,\n'%(' '*(self.indent*3),v["first"])
        s+='%s"draw_count" : %i,\n'%(' '*(self.indent*3),v["count"])
        s+='%s"color" : [%g,%g,%g,%g],\n'%(' '*(self.indent*3),
                                           v["color"][0],
                                           v["color"][1],
                                           v["color"][2],
                                           v["alpha"])
        s+='%s"emit" : %g,\n'%(' '*(self.indent*3),v["emit"])
        s+='%s"fresnel" : %g,\n'%(' '*(self.indent*3),v["fresnel"])
        s+='%s"fresnel_factor" : %g,\n'%(' '*(self.indent*3),v["fresnel_factor"])
        s+='%s"roughness" : %g,\n'%(' '*(self.indent*3),v["roughness"])
        s+='%s"hardness" : %g,\n'%(' '*(self.indent*3),v["hardness"])
        s+='%s"intensity" : %g\n'%(' '*(self.indent*3),v["intensity"])
        s+='%s}'%(' '*(self.indent*2))

        if not (i==len(mes["material_names"])-1):
          s+=','

        s+='\n'

        fh.write(s)

      fh.write('%s}\n'%(' '*self.indent))


      #
      fh.write('}\n')




    print('Exported to "%s".'%self.filepath)
    return {'FINISHED'};

def menu_func(self, context):
  self.layout.operator(MyExportJson.bl_idname, text="Simple Mesh (.json)");

def register():
  bpy.utils.register_module(__name__);
  bpy.types.INFO_MT_file_export.append(menu_func);

def unregister():
  bpy.utils.unregister_module(__name__);
  bpy.types.INFO_MT_file_export.remove(menu_func);

if __name__ == "__main__":
  register()
