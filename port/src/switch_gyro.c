#include "switch_gyro.h"

#ifdef __SWITCH__
#include <switch.h>
#include <math.h>
#include <string.h>

static HidSixAxisSensorHandle s_handles[4];
static PadState s_pad;
static int s_inited = 0;

void switchGyroInit(void) {
    if (s_inited) return;

    padConfigureInput(1, HidNpadStyleSet_NpadStandard);
    padInitializeDefault(&s_pad);

    /* Index 0: Handheld, 1: Pro Controller (FullKey), 2: JoyDual Left, 3: JoyDual Right */
    hidGetSixAxisSensorHandles(&s_handles[0], 1, HidNpadIdType_Handheld, HidNpadStyleTag_NpadHandheld);
    hidGetSixAxisSensorHandles(&s_handles[1], 1, HidNpadIdType_No1,      HidNpadStyleTag_NpadFullKey);
    hidGetSixAxisSensorHandles(&s_handles[2], 2, HidNpadIdType_No1,      HidNpadStyleTag_NpadJoyDual);

    for (int i = 0; i < 4; i++) {
        hidStartSixAxisSensor(s_handles[i]);
    }

    s_inited = 1;
}

void switchGyroUpdate(void) {
    if (!s_inited) return;
    padUpdate(&s_pad);
}

static inline float apply_gyro_deadzone(float val, float dz) {
    if (val > dz)  return val - dz;
    if (val < -dz) return val + dz;
    return 0.0f;
}

int switchGyroGet(float *pitch, float *yaw) {
    if (!s_inited) {
        *pitch = 0.0f;
        *yaw = 0.0f;
        return 0;
    }

    HidSixAxisSensorState sixaxis = {0};
    u64 style_set = padGetStyleSet(&s_pad);
    size_t count = 0;

    if (style_set & HidNpadStyleTag_NpadHandheld) {
        count = hidGetSixAxisSensorStates(s_handles[0], &sixaxis, 1);
    } else if (style_set & HidNpadStyleTag_NpadFullKey) {
        count = hidGetSixAxisSensorStates(s_handles[1], &sixaxis, 1);
    } else if (style_set & HidNpadStyleTag_NpadJoyDual) {
        u64 attrib = padGetAttributes(&s_pad);
        /* Prefer Right Joy-Con for aiming, fallback to Left */
        if (attrib & HidNpadAttribute_IsRightConnected)
            count = hidGetSixAxisSensorStates(s_handles[3], &sixaxis, 1);
        else if (attrib & HidNpadAttribute_IsLeftConnected)
            count = hidGetSixAxisSensorStates(s_handles[2], &sixaxis, 1);
    } else {
        /* Fallback: try active handles */
        for (int i = 0; i < 4; i++) {
            if (hidGetSixAxisSensorStates(s_handles[i], &sixaxis, 1) > 0 && sixaxis.sampling_number > 0) {
                count = 1;
                break;
            }
        }
    }

    if (count > 0 && sixaxis.sampling_number > 0) {
        /* Smooth deadzone (0.003 rev/s ~ 1 deg/s) to eliminate resting IMU noise
         * while keeping fine wrist aiming immediately responsive without a threshold jump. */
        float p = apply_gyro_deadzone(sixaxis.angular_velocity.x, 0.003f);
        float y = apply_gyro_deadzone(sixaxis.angular_velocity.y, 0.003f);
        float r = apply_gyro_deadzone(sixaxis.angular_velocity.z, 0.003f);

        float combined_yaw;
        if (style_set & HidNpadStyleTag_NpadHandheld) {
            /* Handheld mode: combine horizontal yaw with steering-wheel roll (screen tilt)
             * so tilting or turning the console moves the aim horizontally. */
            combined_yaw = -y - (r * 0.75f);
        } else {
            /* Tabletop / docked mode (Pro Controller or detached Joy-Con): horizontal aim is
             * driven by pure yaw around the vertical axis. */
            combined_yaw = -y;
        }

        /* Convention:
         * *pitch: positive = pitch DOWN (top tilted forward)
         * *yaw:   positive = turn RIGHT */
        *pitch = p;
        *yaw   = combined_yaw;
        return (p != 0.0f || combined_yaw != 0.0f);
    }

    *pitch = 0.0f;
    *yaw = 0.0f;
    return 0;
}

#else

void switchGyroInit(void) {}
void switchGyroUpdate(void) {}
int  switchGyroGet(float *pitch, float *yaw) {
    if (pitch) *pitch = 0.0f;
    if (yaw)   *yaw = 0.0f;
    return 0;
}

#endif
