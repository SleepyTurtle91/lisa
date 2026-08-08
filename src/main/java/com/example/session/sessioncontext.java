public class SessionContext {
    private ExecutionInterface execution;
    public void setExecution(ExecutionInterface execution) {
        this.execution = execution;
    }
    public void run() {
        execution.execute();
    }
}