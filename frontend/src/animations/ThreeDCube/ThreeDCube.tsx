import UploadIcon from '@mui/icons-material/Upload';
import "./ThreeDCube.css";

interface ThreeDCubeProps {
    show: boolean;
    setShow: (show: boolean) => void;
}

export default function ThreeDCube({ show, setShow }: ThreeDCubeProps) {
    const handleClick = () => {
        setShow(!show);
    };

    return (
        <div className="cube-outer-container" onClick={handleClick}>
            <div className="cube-inner-container">
                <div className="box-card">
                    <div className="face front">
                        <div className="face-content">
                            <UploadIcon style={{ width: 32, height: 32 }} />
                            <div className="face-label">New Spec</div>
                        </div>
                    </div>
                    <div className="face back">
                        <div className="face-content">
                            <UploadIcon style={{ width: 32, height: 32 }} />
                            <div className="face-label">New Spec</div>
                        </div>
                    </div>
                    <div className="face right">
                        <div className="face-content">
                            <UploadIcon style={{ width: 32, height: 32 }} />
                            <div className="face-label">New Spec</div>
                        </div>
                    </div>
                    <div className="face left">
                        <div className="face-content">
                            <UploadIcon style={{ width: 32, height: 32 }} />
                            <div className="face-label">New Spec</div>
                        </div>
                    </div>
                    <div className="face top">
                        <div className="face-content">
                            <UploadIcon style={{ width: 32, height: 32 }} />
                            <div className="face-label">New Spec</div>
                        </div>
                    </div>
                    <div className="face bottom">
                        <div className="face-content">
                            <UploadIcon style={{ width: 32, height: 32 }} />
                            <div className="face-label">New Spec</div>
                        </div>
                    </div>
                </div>
            </div >
        </div>
    );
}
