"""Turnaround wording follows the installed Pruna identity-sheet guidance."""
import math


def turnaround_prompt(recipe):
    t=recipe['turnaround'];views=t['views'];count=len(views);cols=t['columns'];rows=math.ceil(count/cols)
    panel_count='four' if count==4 else str(count)
    pose={'neutral':'relaxed neutral stance, arms slightly separated from the body', 'a-pose':'neutral A pose with straight arms angled downward', 't-pose':'neutral T pose with arms horizontal', 'rigid':'unchanging rigid construction'}[t['pose']]
    if t['subject']!='character': pose='unchanging rigid construction; no articulation or configuration changes'
    camera='orthographic projection with parallel lines' if t['projection']=='orthographic' else f"weak perspective, long-lens camera with {t['fov']}° field of view"
    order='; '.join(f"panel {i+1}: {v['label'].replace('-',' ')} view, camera azimuth {v['azimuth']:g}°" for i,v in enumerate(views))
    return (f"Create a clean {t['subject']} turnaround reference sheet of {recipe['prompt']}\n"
        f"Exactly {panel_count} equal rectangular panels arranged in {rows} row(s) and {cols} columns. Read left to right, then top to bottom: {order}.\n"
        f"Camera convention: 0° sees the front, 90° sees the subject's left side, 180° sees the back, 270° sees its right side. {camera}; elevation {t['elevation']}°, zero roll, aimed at the subject center.\n"
        f"The exact same subject in every panel, identical face, proportions, materials, costume and equipment. {pose} in every view. Rotate only the camera around the subject. Do not mirror the subject or move asymmetrical details to the opposite side.\n"
        "Use the same camera distance, magnification, ground line and subject scale in every panel. Show the complete silhouette with generous clear margins; no clipping, overlap or touching panel edges. "
        "Neutral seamless gray background #c8c8c8, soft even studio lighting, identical rendering style. No story environment, added props, panel borders, labels or text.\n"
        f"Unchanging details: {t['locks'] or 'Preserve all identifying details from the supplied references and description.'}")
