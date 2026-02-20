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
        <div className="cube-outer-container">
            <div className="cube-inner-container">
                <div className="box-card">
                    <div className="face front" onClick={handleClick}>
                        <UploadIcon />
                        <span>Upload a new spec</span>
                    </div>
                    <div className="face back" onClick={handleClick}>
                        <UploadIcon />
                        <span>Upload a new spec</span>
                    </div>
                    <div className="face right" onClick={handleClick}>
                        <UploadIcon />
                        <span>Upload a new spec</span>
                    </div>
                    <div className="face left" onClick={handleClick}>
                        <UploadIcon />
                        <span>Upload a new spec</span>
                    </div>
                    <div className="face top" onClick={handleClick}>
                        <UploadIcon />
                        <span>Upload a new spec</span>
                    </div>
                    <div className="face bottom" onClick={handleClick}>
                        <UploadIcon />
                        <span>Upload a new spec</span>
                    </div>
                </div>
            </div >
        </div>
    );
}
