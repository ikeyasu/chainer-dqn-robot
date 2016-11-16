//  File deep-insect is modified by ikeyasu 11/2016
//  Original file SerialCamera.pde for camera.
//  25/7/2011 by Piggy
//  Modify by Deray  08/08/2012

#include <SoftwareSerial.h>
#include <ESP8266WiFi.h>
#include <ESP8266WiFiMulti.h>
#include <ESP8266HTTPClient.h>
#include <Wire.h>

SoftwareSerial gCamSerial(12, 13, false, 256); //receivePin, transmitPin, inverse_logic, buffSize

/**** camera *****/
#define PIC_PKT_LEN    2048                  //data length of each read, dont set this too big because ram is limited
#define PIC_FMT_VGA    7
#define PIC_FMT_CIF    5
#define PIC_FMT_OCIF   3
#define CAM_ADDR       0
#define PIC_FMT        PIC_FMT_OCIF
const byte gCameraAddr = (CAM_ADDR << 5);  // addr

/*** motor ***/
#define MotorSpeedSet             0x82
#define PWMFrequenceSet           0x84
#define DirectionSet              0xaa
#define MotorSetA                 0xa1
#define MotorSetB                 0xa5
#define Nothing                   0x01
#define EnableStepper             0x1a
#define UnenableStepper           0x1b
#define Stepernu                  0x1c
#define I2CMotorDriverAdd         0x0f   // Set the address of the I2CMotorDriver
// set the steps you want, if 255, the stepper will rotate continuely;


/*** others ***/
char* gURL = "http://ikeuchis-air.localnet:5000/?????????????????????????????"; // need a buffer for URL query param
#define URL_LEN 35
unsigned long gPicTotalLen = 0;  // picture length
ESP8266WiFiMulti gWifiMulti;
HTTPClient gHttp;

char ACTIONS[9][2] = {
       {-1, -1}, // 0
       {-1,  0}, // 1
       {-1,  1}, // 2
       { 0, -1}, // 3
       { 0,  0}, // 4
       { 0,  1}, // 5
       { 1, -1}, // 6
       { 1,  0}, // 7
       { 1,  1}};// 8

void setup()
{
  Serial.begin(115200);
  gCamSerial.begin(115200);
  Wire.begin();
  delayMicroseconds(10000);
  MotorSpeedSetAB(0, 0);

  Serial.println("initialization done.");
  initCamera();
  gWifiMulti.addAP("F660A-gTbC-G", "a2QLYvUu");
  gHttp.setReuse(true);

  Serial.print("wifi connecting ..");
  while ((gWifiMulti.run() != WL_CONNECTED)) {
    delay(500);
    Serial.print(".");
  }
  delay(1000);
  Serial.println("connected.");
  Serial.print("test connection ...");
  int httpCode = 0;
  while (httpCode != 200) {
    gHttp.begin(gURL);
    httpCode = gHttp.GET();
    Serial.print(".");
    Serial.print(httpCode);
    gHttp.end();
  }
  Serial.println(".done.");
  initCapture();
}

void loop()
{
  static int n = 0;

  Serial.println("Start to take a picture");
  capture();
  char action = getAndSendData(n);
  doAction(action);
  Serial.print("Taking pictures success ,number : ");
  Serial.println(n);
  n++;
  Serial.println();
}

void initCamera()
{
  char cmd[] = {0xaa, 0x0d | gCameraAddr, 0x00, 0x00, 0x00, 0x00} ;
  unsigned char resp[6];

  gCamSerial.setTimeout(500);
  while (1) {
    //clearRxBuf();
    sendCmd(cmd, 6);
    if (gCamSerial.readBytes((char *)resp, 6) != 6) {
      continue;
    }
    if (resp[0] == 0xaa && resp[1] == (0x0e | gCameraAddr) && resp[2] == 0x0d && resp[4] == 0 && resp[5] == 0) {
      if (gCamSerial.readBytes((char *)resp, 6) != 6) continue;
      if (resp[0] == 0xaa && resp[1] == (0x0d | gCameraAddr) && resp[2] == 0 && resp[3] == 0 && resp[4] == 0 && resp[5] == 0) break;
    }
  }
  cmd[1] = 0x0e | gCameraAddr;
  cmd[2] = 0x0d;
  sendCmd(cmd, 6);
  Serial.println("Camera initialization done.");
}

void initCapture()
{
  char cmd[] = { 0xaa, 0x01 | gCameraAddr, 0x00, 0x07, 0x00, PIC_FMT };
  unsigned char resp[6];

  gCamSerial.setTimeout(100);
  while (1) {
    clearRxBuf();
    sendCmd(cmd, 6);
    if (gCamSerial.readBytes((char *)resp, 6) != 6) continue;
    if (resp[0] == 0xaa && resp[1] == (0x0e | gCameraAddr) && resp[2] == 0x01 && resp[4] == 0 && resp[5] == 0) break;
  }
  Serial.println("Capture initialization done.");
}

void capture() {
  char cmd[] = { 0xaa, 0x06 | gCameraAddr, 0x08, PIC_PKT_LEN & 0xff, (PIC_PKT_LEN >> 8) & 0xff , 0};
  unsigned char resp[6];

  gCamSerial.setTimeout(100);
  while (1) {
    clearRxBuf();
    sendCmd(cmd, 6);
    if (gCamSerial.readBytes((char *)resp, 6) != 6) continue;
    if (resp[0] == 0xaa && resp[1] == (0x0e | gCameraAddr) && resp[2] == 0x06 && resp[4] == 0 && resp[5] == 0) break;
  }
  cmd[1] = 0x05 | gCameraAddr;
  cmd[2] = 0;
  cmd[3] = 0;
  cmd[4] = 0;
  cmd[5] = 0;
  while (1) {
    clearRxBuf();
    sendCmd(cmd, 6);
    if (gCamSerial.readBytes((char *)resp, 6) != 6) continue;
    if (resp[0] == 0xaa && resp[1] == (0x0e | gCameraAddr) && resp[2] == 0x05 && resp[4] == 0 && resp[5] == 0) break;
  }
  cmd[1] = 0x04 | gCameraAddr;
  cmd[2] = 0x1;
  while (1) {
    clearRxBuf();
    sendCmd(cmd, 6);
    if (gCamSerial.readBytes((char *)resp, 6) != 6) continue;
    if (resp[0] == 0xaa && resp[1] == (0x0e | gCameraAddr) && resp[2] == 0x04 && resp[4] == 0 && resp[5] == 0)
    {
      gCamSerial.setTimeout(1000);
      if (gCamSerial.readBytes((char *)resp, 6) != 6)
      {
        continue;
      }
      if (resp[0] == 0xaa && resp[1] == (0x0a | gCameraAddr) && resp[2] == 0x01)
      {
        gPicTotalLen = (resp[3]) | (resp[4] << 8) | (resp[5] << 16);
        break;
      }
    }
  }
}

void clearRxBuf() {
  while (Serial.available()) gCamSerial.read();
}

int skipLF(char in[], int len) {
  int skip = 0;
  for (int i = 0; i + skip < len; i++) {
    if (in[i] == '\n') skip++;
    in[i] = in[i + skip];
  }
  return len - skip;
}

char getAndSendData(int index) {
  unsigned int pktCnt = (gPicTotalLen) / (PIC_PKT_LEN - 6);
  if ((gPicTotalLen % (PIC_PKT_LEN - 6)) != 0) pktCnt += 1;

  char cmd[] = { 0xaa, 0x0e | gCameraAddr, 0x00, 0x00, 0x00, 0x00 };
  char pkt[PIC_PKT_LEN];
  char result;

  gCamSerial.setTimeout(1000);
  for (unsigned int i = 0; i < pktCnt; i++) {
    cmd[4] = i & 0xff;
    cmd[5] = (i >> 8) & 0xff;

    int retry_cnt = 0;
retry:
    delay(10);
    clearRxBuf();
    sendCmd(cmd, 6);
    uint16_t cnt = gCamSerial.readBytes((char *)pkt, PIC_PKT_LEN);

    unsigned char sum = 0;
    for (int y = 0; y < cnt - 2; y++) {
      sum += pkt[y];
    }
    if (sum != pkt[cnt - 2]) {
      if (++retry_cnt < 100) goto retry;
      else break;
    }
    int urlLen = 0; //strlen(URL);
    sprintf(gURL + URL_LEN, "n=%d&last=%s", index, (i == pktCnt - 1) ? "y" : "n");
    gHttp.begin(gURL);
    int httpCode = gHttp.POST((uint8_t *) &pkt[4], cnt - 6);
    if (httpCode == 200 && gHttp.getSize() == 1) {
      String payload = gHttp.getString();
      result = (payload == "-") ? -1 : payload.toInt();
      Serial.print("getAndSendData: result=");
      Serial.println(result, DEC);
    }
    gHttp.end();
  }
  cmd[4] = 0xf0;
  cmd[5] = 0xf0;
  sendCmd(cmd, 6);
  return result;
}

void sendCmd(char cmd[] , int cmd_len) {
  for (char i = 0; i < cmd_len; i++) gCamSerial.print(cmd[i]);
}

void doAction(char action) {
  Serial.print("action=");
  Serial.print(ACTIONS[action][0], DEC);
  Serial.print(",");
  Serial.println(ACTIONS[action][1], DEC);
  MotorSpeedSetAB(ACTIONS[action][0] == 0 ? 0 : 30, ACTIONS[action][1] == 0 ? 0 : 30);
  delay(10); //this delay needed
  //"0b1010" defines the output polarity, "10" means the M+ is "positive" while the M- is "negtive"
  unsigned char dir = ACTIONS[action][0] > 0 ? 0b10 : 0b01;
  dir <<= 2;
  dir |= ACTIONS[action][1] > 0 ? 0b10 : 0b01;
  MotorDirectionSet(dir);
  Serial.print("doAction: dir=0b");
  Serial.println(dir, BIN);
  delay(250);
  MotorSpeedSetAB(0, 0);
  delay(10); //this delay needed
  MotorDirectionSet(0b0101);  //0b0101  Rotating in the opposite direction
  Serial.println("doAction: motor stoped.");
}

void MotorSpeedSetAB(unsigned char MotorSpeedA , unsigned char MotorSpeedB)  {
  MotorSpeedA=map(MotorSpeedA,0,100,0,255);
  MotorSpeedB=map(MotorSpeedB,0,100,0,255);
  Wire.beginTransmission(I2CMotorDriverAdd); // transmit to device I2CMotorDriverAdd
  Wire.write(MotorSpeedSet);        // set pwm header
  Wire.write(MotorSpeedA);              // send pwma
  Wire.write(MotorSpeedB);              // send pwmb
  Wire.endTransmission();    // stop transmittin
}

void MotorPWMFrequenceSet(unsigned char Frequence)  {
  Wire.beginTransmission(I2CMotorDriverAdd); // transmit to device I2CMotorDriverAdd
  Wire.write(PWMFrequenceSet);        // set frequence header
  Wire.write(Frequence);              //  send frequence
  Wire.write(Nothing);              //  need to send this byte as the third byte(no meaning)
  Wire.endTransmission();    // stop transmitting
}

void MotorDirectionSet(unsigned char Direction)  {     //  Adjust the direction of the motors 0b0000 I4 I3 I2 I1
  Wire.beginTransmission(I2CMotorDriverAdd); // transmit to device I2CMotorDriverAdd
  Wire.write(DirectionSet);        // Direction control header
  Wire.write(Direction);              // send direction control information
  Wire.write(Nothing);              // need to send this byte as the third byte(no meaning)
  Wire.endTransmission();    // stop transmitting
}

