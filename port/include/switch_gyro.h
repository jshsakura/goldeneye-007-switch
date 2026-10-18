#pragma once

#ifdef __cplusplus
extern "C" {
#endif

void switchGyroInit(void);
void switchGyroUpdate(void);
/* Returns 1 if valid gyro motion was read, 0 otherwise */
int  switchGyroGet(float *pitch, float *yaw);

#ifdef __cplusplus
}
#endif
