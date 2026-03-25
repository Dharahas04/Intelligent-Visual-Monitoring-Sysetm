package com.major.unifiedmonitoring.live;

public class LiveFrameMessage {

    private String type;
    private String serviceType;
    private String frameData;
    private Long clientTs;

    public String getType() {
        return type;
    }

    public void setType(String type) {
        this.type = type;
    }

    public String getServiceType() {
        return serviceType;
    }

    public void setServiceType(String serviceType) {
        this.serviceType = serviceType;
    }

    public String getFrameData() {
        return frameData;
    }

    public void setFrameData(String frameData) {
        this.frameData = frameData;
    }

    public Long getClientTs() {
        return clientTs;
    }

    public void setClientTs(Long clientTs) {
        this.clientTs = clientTs;
    }
}
