import numpy as np
import cv2
import argparse as ap
import _pickle as cPickle
import os
import matplotlib.pyplot as plt
from wild6d_mesh import virtual_correspondence, load_data as load_vc_data


def load_data(data_dir, object_type):
    image_path = os.path.join(data_dir, object_type, 'raw', 'images')
    wild6d_result_path = os.path.join(data_dir, object_type, 'results2')
    image_list = [os.path.join(image_path, f) for f in os.listdir(image_path)]
    pkl_list = sorted([os.path.join(wild6d_result_path, f) for f in os.listdir(wild6d_result_path) if '.pkl' in f])
    pkl_data = [cPickle.load(open(pkl, 'rb')) for pkl in pkl_list]
    data = {
        'image_list': image_list,
        'pkl_data': pkl_data
    }
    return data


def generate_random_pairs(num_pairs, min_val=1, max_val=200):
    pairs = []
    for i in range(num_pairs):
        pairs.append(np.random.randint(min_val, max_val, size=2))
    return np.array(pairs)

def generate_seq_pairs(num_pairs, min_val=1, max_val=200):
    pairs = []
    for i in range(num_pairs-1):
        pairs.append(np.array([0, i+1]))
    return np.array(pairs)


def recover_pose(kps1, kps2, K, method=cv2.RANSAC):
    E, mask = cv2.findEssentialMat(kps1, kps2, cameraMatrix=K, method=method)
    retval, R, t, mask = cv2.recoverPose(E, kps2, kps1, cameraMatrix=K)
    return E, R, t

def get_3d_bbox(size, shift=0):
    bbox_3d = np.array([[+size[0] / 2, +size[1] / 2, +size[2] / 2],
                        [+size[0] / 2, +size[1] / 2, -size[2] / 2],
                        [-size[0] / 2, +size[1] / 2, +size[2] / 2],
                        [-size[0] / 2, +size[1] / 2, -size[2] / 2],
                        [+size[0] / 2, -size[1] / 2, +size[2] / 2],
                        [+size[0] / 2, -size[1] / 2, -size[2] / 2],
                        [-size[0] / 2, -size[1] / 2, +size[2] / 2],
                        [-size[0] / 2, -size[1] / 2, -size[2] / 2]]) + shift
    return bbox_3d.T

def transform_coordinates_3d(coordinates, sRT):
    """
    Args:
        coordinates: [3, N]
        sRT: [4, 4]

    Returns:
        new_coordinates: [3, N]

    """
    assert coordinates.shape[0] == 3
    coordinates = np.vstack([coordinates, np.ones((1, coordinates.shape[1]), dtype=np.float32)])
    new_coordinates = sRT @ coordinates
    new_coordinates = new_coordinates[:3, :] / new_coordinates[3, :]
    return new_coordinates

def calculate_2d_projections(coordinates_3d, intrinsics):
    """
    Args:
        coordinates_3d: [3, N]
        intrinsics: [3, 3]

    Returns:
        projected_coordinates: [N, 2]
    """
    projected_coordinates = intrinsics @ coordinates_3d
    projected_coordinates = projected_coordinates[:2, :] / projected_coordinates[2, :]
    projected_coordinates = projected_coordinates.transpose()
    projected_coordinates = np.array(projected_coordinates, dtype=np.int32)

    return projected_coordinates

def match_scales(data1, data2, box_type='gt', scales=[0.1, 0.1, 0.1]):
    if box_type=='gt':
        gtrts1 = data1['gt_RTs']
        gtrts2 = data2['gt_RTs']
    elif box_type=='pred':
        gtrts1 = data1['pred_RTs']
        gtrts2 = data2['pred_RTs']
    # box1 = data1['gt_3d_box'].T
    # box2 = data2['gt_3d_box'].T
    # box1_ = np.hstack((box1, np.ones((box1.shape[0], 1))))
    # box2_ = np.hstack((box2, np.ones((box2.shape[0], 1))))
    # inv1 = np.linalg.inv(gtrts1[0])
    # inv2 = np.linalg.inv(gtrts2[0])
    # box1_ = (inv1 @ box1_.T).T
    # box2_ = (inv2 @ box2_.T).T
    # box1_ = box1_/box1_[:, 3:]
    # box2_ = box2_/box2_[:, 3:]
    box1 = get_3d_bbox(scales)
    box3d1 = transform_coordinates_3d(box1, gtrts1[0])
    proj_box1 = calculate_2d_projections(box3d1, data1['K'])

    box2 = get_3d_bbox(scales)
    box3d2 = transform_coordinates_3d(box2, gtrts2[0])
    proj_box2 = calculate_2d_projections(box3d2, data2['K'])
    return proj_box1, proj_box2



def relative_pose(data1, data2):
    K = data1['K']
    match_scales(data1, data2)
    # kps1_pred = data1['pred_proj_box']
    # kps2_pred = data2['pred_proj_box']
    # kps1_gt = data1['gt_proj_box']
    # kps2_gt = data2['gt_proj_box']
    kps1_gt, kps2_gt = match_scales(data1, data2, box_type='gt')
    kps1_pred, kps2_pred = match_scales(data1, data2, box_type='pred')
    # kps1_gt1, kps2_gt1 = match_scales(data1, data2, scales=[0.2, 0.2, 0.2])
    # temp1 = data1['gt_3d_box'].T # pts in camera frame
    # temp2 = data2['gt_3d_box'].T
    # print(data1['gt_scales'])
    # print(data2['gt_scales'])
    # temp1 = np.hstack((temp1, np.ones((temp1.shape[0], 1))))
    # temp2 = np.hstack((temp2, np.ones((temp2.shape[0], 1))))
    # pts = temp1[:,:3]
    # pts2 = temp2[:,:3]
    # pix = (K @ pts.T).T
    # pix = pix / pix[:, 2:]
    # pix2 = (K @ pts2.T).T
    # pix2 = pix2 / pix2[:, 2:]
    # print(pix)
    # print(pix2)
    # print(kps1_gt)
    # print(kps2_gt)
    # E_pred, R_pred, t_pred = recover_pose(kps1_pred, kps2_pred, K)
    E_gt, R_gt, t_gt = recover_pose(kps1_gt, kps2_gt, K)
    E_pred, R_pred, t_pred = recover_pose(kps1_pred, kps2_pred, K)
    # E_pred_, R_gt2, t_gt2 = recover_pose(kps1_gt1, kps2_gt1, K)
    # print(compute_rotation_error(R_gt2, R_gt))
    # E_gt2, R_gt2, t_gt2 = recover_pose(pix[:,:2], pix2[:,:2], K)
    return R_pred, R_gt

def relative_rotation(R1, R2):
    # return np.linalg.inv(R2) @ R1
    return np.linalg.inv(R1) @ R2
    # return R1 @ np.linalg.inv(R2)

def compute_rotation_error(sRT_1, sRT_2):
    R1 = sRT_1[:3, :3] / np.cbrt(np.linalg.det(sRT_1[:3, :3]))
    R2 = sRT_2[:3, :3] / np.cbrt(np.linalg.det(sRT_2[:3, :3]))
    # # symmetric when rotating around y-axis
    # if synset_names[class_id] in ['bottle', 'can', 'bowl'] or \
    #     (synset_names[class_id] == 'mug' and handle_visibility == 0):
    #     y = np.array([0, 1, 0])
    #     y1 = R1 @ y
    #     y2 = R2 @ y
    #     cos_theta = y1.dot(y2) / (np.linalg.norm(y1) * np.linalg.norm(y2))
    # else:
    R = R1 @ R2.transpose()
    cos_theta = (np.trace(R) - 1) / 2
    theta = np.arccos(np.clip(cos_theta, -1.0, 1.0)) * 180 / np.pi

    return theta

# def vc_pose(match_data1, K):
def vc_pose(fp1, fp2, K):
    faces1 = set(list(fp1.keys()))
    faces2 = set(list(fp2.keys()))
    common_faces = faces1.intersection(faces2)

    view1 = []
    view2 = []

    for fid in common_faces:
        px1 = fp1[fid]
        px2 = fp2[fid]
        view1.append(px1.mean(axis=0))
        view2.append(px2.mean(axis=0))
    view1 = np.array(view1)[:, :2][:, np.newaxis, :]
    view2 = np.array(view2)[:, :2][:, np.newaxis, :]

    F, mask = cv2.findFundamentalMat(view2, view1, method=cv2.USAC_ACCURATE)
    E = K.T @ F @ K
    retval, R, t, mask = cv2.recoverPose(E, view2, view1, cameraMatrix=K)

    inlier_points1 = view1[mask.ravel() == 1]
    inlier_points2 = view2[mask.ravel() == 1]

    print (view1.shape, view2.shape)
    print (inlier_points1.shape, inlier_points2.shape)
    print (F)
    return R

def main(args):
    data = load_data(args.data_dir, args.object)
    data_vc = load_vc_data(args.data_dir, args.object)
    rand_pairs = generate_random_pairs(100, max_val=len(data['pkl_data']))
    base_verts, base_faces = data_vc['mesh_data']
    # rand_pairs = generate_seq_pairs(len(data['pkl_data']))
    errs = []
    for p in rand_pairs[:,:]:
        R_pred, R_gt_proj = relative_pose(data['pkl_data'][p[0]], data['pkl_data'][p[1]])
        fp1, fp2 = virtual_correspondence(data_vc, [p[0], p[1]], base_verts, base_faces, viz=False)
        R_vc = vc_pose(fp1, fp2, data['pkl_data'][p[0]]['K'])
        gt_RTs_0 = data['pkl_data'][p[0]]['gt_RTs']
        gt_RTs_1 = data['pkl_data'][p[1]]['gt_RTs']
        pred_RTs_0 = data['pkl_data'][p[0]]['pred_RTs']
        pred_RTs_1 = data['pkl_data'][p[1]]['pred_RTs']
        R_gt = relative_rotation(gt_RTs_0[0][:3, :3], gt_RTs_1[0][:3, :3])
        R_preds = relative_rotation(pred_RTs_0[0][:3, :3], pred_RTs_1[0][:3, :3])
        err1 = compute_rotation_error(R_pred, R_gt)         # b/w green box and gt
        err2 = compute_rotation_error(R_gt_proj, R_gt)      # b/w red box and gt
        err3 = compute_rotation_error(R_preds, R_gt)
        err4 = compute_rotation_error(R_vc, R_gt)
        errs.append([err1, err2, err3, err4])
        print("Rotation error with predicions :: {:.3f} \t \
               Rotation error with gt :: {:.3f} \t \
               Rotation error baseline 1 :: {:.3f} \t \
                Rotation error vc :: {:.3f}".format(err1, err2, err3, err4))
    errs = np.array(errs)
    print(np.mean(errs[:,3]))
    errs_b1 = errs[:,3]
    errs_b1 = errs_b1[errs_b1 < 80]
    print(np.mean(errs_b1))
    plt.hist(errs[:,3])
    plt.show()


if __name__ == '__main__':
    ap = ap.ArgumentParser()
    ap.add_argument('-d', '--data_dir', default='./data/', help='Path to data directory')
    ap.add_argument('-o', '--object', choices=['bottle', 'bowl', 'camera', 'can', 'laptop', 'mug'],default='camera', help='Object set to use')
    args = ap.parse_args()
    main(args)